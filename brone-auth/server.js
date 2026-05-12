const express = require('express');
const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');

puppeteer.use(StealthPlugin());

const app = express();
app.use(express.json());

app.use('/media', express.static('public'));

const CHROME_ARGS = [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage',
    '--disable-blink-features=AutomationControlled',
    '--disable-crash-reporter',
    '--disable-crashpad',
    '--disable-gpu',
    '--disable-breakpad',
    '--no-zygote'
];

const SHORT_WAIT_MS = 800;

function createLaunchOptions() {
    return {
        headless: 'new',
        executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || '/usr/bin/google-chrome-stable',
        args: CHROME_ARGS
    };
}

const activeBrowsers = new Set();

function trackBrowser(browser) {
    activeBrowsers.add(browser);
    browser.once('disconnected', () => activeBrowsers.delete(browser));
    return browser;
}

async function closeBrowserSafely(browser, context = '[BROWSER]') {
    if (!browser) return;
    try {
        await browser.close();
    } catch (error) {
        console.error(`${context} Failed to close browser cleanly:`, error.message);
        const processHandle = browser.process?.();
        if (processHandle?.pid) {
            process.kill(processHandle.pid, 'SIGKILL');
        }
    } finally {
        activeBrowsers.delete(browser);
    }
}

let server;
let shuttingDown = false;

async function shutdown(signal) {
    if (shuttingDown) return;
    shuttingDown = true;
    console.log(`[INFO][BOOT] Received ${signal}, shutting down gracefully...`);
    if (server) {
        await new Promise((resolve) => server.close(resolve));
    }
    await Promise.allSettled(
        Array.from(activeBrowsers).map((browser) => closeBrowserSafely(browser, '[INFO][BOOT]'))
    );
    process.exit(0);
}

process.on('SIGTERM', () => {
    void shutdown('SIGTERM');
});
process.on('SIGINT', () => {
    void shutdown('SIGINT');
});

class ServiceError extends Error {
    constructor(code, message, details = {}, statusCode = 500) {
        super(message);
        this.name = 'ServiceError';
        this.code = code;
        this.details = details;
        this.statusCode = statusCode;
    }
}

const SIAM_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36';
const SIAM_AUTH_MAX_ATTEMPTS = Number(process.env.SIAM_AUTH_MAX_ATTEMPTS || 3);
const SIAM_TOKEN_POLL_COUNT = Number(process.env.SIAM_TOKEN_POLL_COUNT || 12);
const SIAM_TOKEN_POLL_INTERVAL_MS = Number(process.env.SIAM_TOKEN_POLL_INTERVAL_MS || 500);
const SIAM_COOLDOWN_THRESHOLD = Number(process.env.SIAM_COOLDOWN_THRESHOLD || 5);
const SIAM_COOLDOWN_MS = Number(process.env.SIAM_COOLDOWN_MS || 45000);

const siamAuthRuntime = {
    consecutiveFailures: 0,
    cooldownUntil: 0,
    lastSuccessAt: null,
    lastFailureAt: null,
    lastErrorCode: null
};

function createRequestId(prefix = 'req') {
    return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function retryDelayMs(attempt) {
    const jitter = Math.floor(Math.random() * 400);
    return 900 * attempt + jitter;
}

function normalizeError(error, fallbackCode = 'INTERNAL_ERROR', fallbackStatus = 500) {
    if (error instanceof ServiceError) return error;
    return new ServiceError(fallbackCode, error?.message || 'Unknown error.', {}, fallbackStatus);
}

function isLikelyTransientNetworkError(error) {
    const message = String(error?.message || '').toLowerCase();
    return (
        message.includes('err_aborted') ||
        message.includes('net::err') ||
        message.includes('navigation timeout') ||
        message.includes('timed out') ||
        message.includes('execution context was destroyed') ||
        message.includes('target closed') ||
        message.includes('detached') ||
        message.includes('socket hang up')
    );
}

async function warmupSiamPresensiPage(page, meta = {}) {
    const endpoint = meta.endpoint || 'unknown';
    const requestId = meta.requestId || createRequestId('presensi');
    const attempt = meta.attempt || 1;
    const warmupTimeoutMs = Number(process.env.SIAM_PRESENSI_WARMUP_TIMEOUT_MS || 15000);

    console.log(`[INFO][PRESENSI][${endpoint}][${requestId}] attempt=${attempt} Warmup presensi page...`);
    try {
        await page.goto('https://siam.ub.ac.id/mahasiswa/presensi', {
            waitUntil: 'domcontentloaded',
            timeout: warmupTimeoutMs
        });
        await sleep(SHORT_WAIT_MS);
    } catch (error) {
        const normalized = normalizeError(error, 'SIAM_PRESENSI_WARMUP_FAILED', 502);
        console.warn(
            `[WARN][PRESENSI][${endpoint}][${requestId}] attempt=${attempt} warmupSkipped=true code=${normalized.code} message=${normalized.message}`
        );
    }
}

function sendError(res, requestId, error, fallbackStatus = 500) {
    const normalized = normalizeError(error, 'INTERNAL_ERROR', fallbackStatus);
    const body = {
        success: false,
        requestId,
        code: normalized.code,
        error: normalized.message
    };
    if (normalized.details && Object.keys(normalized.details).length > 0) {
        body.details = normalized.details;
    }
    res.status(normalized.statusCode || fallbackStatus).json(body);
}

function registerSiamSuccess() {
    siamAuthRuntime.consecutiveFailures = 0;
    siamAuthRuntime.cooldownUntil = 0;
    siamAuthRuntime.lastErrorCode = null;
    siamAuthRuntime.lastSuccessAt = new Date().toISOString();
}

function registerSiamFailure(errorCode) {
    siamAuthRuntime.consecutiveFailures += 1;
    siamAuthRuntime.lastFailureAt = new Date().toISOString();
    siamAuthRuntime.lastErrorCode = errorCode || 'UNKNOWN';
    if (siamAuthRuntime.consecutiveFailures >= SIAM_COOLDOWN_THRESHOLD) {
        siamAuthRuntime.cooldownUntil = Date.now() + SIAM_COOLDOWN_MS;
    }
}

function getSiamCooldownError() {
    const remainingMs = siamAuthRuntime.cooldownUntil - Date.now();
    if (remainingMs <= 0) return null;
    return new ServiceError(
        'SIAM_COOLDOWN_ACTIVE',
        'SIAM auth is in temporary cooldown after repeated failures.',
        { retryAfterMs: remainingMs },
        503
    );
}

async function prepareSiamPage(page) {
    await page.evaluateOnNewDocument(() => {
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
    });
    await page.setUserAgent(SIAM_USER_AGENT);
}

async function getSiamUiState(page) {
    return page.evaluate(() => {
        const loginButton = document.querySelector('button.btn-primary');
        const loginButtonText = loginButton ? loginButton.textContent?.trim() : null;
        const keycloakToken = (typeof Sso_ub !== 'undefined' && Sso_ub.KEYCLOAK && Sso_ub.KEYCLOAK.token)
            ? Sso_ub.KEYCLOAK.token
            : null;
        return {
            currentUrl: location.href,
            loginButtonVisible: Boolean(loginButton),
            loginButtonText: loginButtonText || null,
            hasRuntimeToken: Boolean(keycloakToken),
            dataAuthLength: (localStorage.getItem('dataAuth') || '').length
        };
    });
}

async function extractBearerTokenFromRuntime(page) {
    const token = await page.evaluate(() => {
        const keycloakToken = (typeof Sso_ub !== 'undefined' && Sso_ub.KEYCLOAK && Sso_ub.KEYCLOAK.token)
            ? Sso_ub.KEYCLOAK.token
            : null;
        if (keycloakToken) return keycloakToken;

        const rawDataAuth = localStorage.getItem('dataAuth');
        if (!rawDataAuth) return null;

        try {
            let decoded = rawDataAuth;
            if (typeof isDevel !== 'undefined' && isDevel === '0' && typeof CryptoJS !== 'undefined' && typeof secret !== 'undefined') {
                decoded = CryptoJS.AES.decrypt(rawDataAuth, secret).toString(CryptoJS.enc.Utf8);
            }
            const parsed = JSON.parse(decoded);
            return parsed?.token || null;
        } catch {
            return null;
        }
    });

    if (!token) return null;
    if (/^Bearer\s+/i.test(token)) return token;
    return `Bearer ${token}`;
}

async function getSiamAuth(page, username, password, meta = {}) {
    const requestId = meta.requestId || createRequestId('siam');
    const attempt = meta.attempt || 1;
    let capturedToken = null;
    let tokenSource = null;
    let tokenEndpointStatus = null;
    let accountEndpointStatus = null;
    let finalUiState = null;

    const onRequest = (request) => {
        const headers = request.headers();
        const authHeader = headers.authorization || headers.Authorization;
        if (!capturedToken && typeof authHeader === 'string' && /^bearer\s+/i.test(authHeader)) {
            capturedToken = authHeader;
            tokenSource = `request_header:${request.url()}`;
        }
    };

    const onResponse = async (response) => {
        const url = response.url();

        if (url.includes('/protocol/openid-connect/token')) {
            tokenEndpointStatus = response.status();
            if (!capturedToken && response.status() === 200) {
                try {
                    const data = await response.json();
                    if (data?.access_token) {
                        capturedToken = `Bearer ${data.access_token}`;
                        tokenSource = 'keycloak_token_response';
                    }
                } catch {
                    // ignored
                }
            }
        }

        if (url.endsWith('/auth/realms/ub/account')) {
            accountEndpointStatus = response.status();
        }
    };

    try {
        page.on('request', onRequest);
        page.on('response', onResponse);

        console.log(`[INFO][SIAM][AUTH][${requestId}] attempt=${attempt} Starting authentication flow...`);
        await page.goto('https://siam.ub.ac.id', { waitUntil: 'networkidle2' });

        await page.waitForSelector('button.btn-primary', { visible: true, timeout: 15000 });
        await page.click('button.btn-primary');

        await page.waitForSelector('#username', { visible: true, timeout: 30000 });
        await page.type('#username', username, { delay: 20 });
        await page.type('#password', password, { delay: 20 });

        await Promise.all([
            page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 45000 }),
            page.click('#kc-login')
        ]);

        for (let i = 0; i < SIAM_TOKEN_POLL_COUNT; i += 1) {
            if (!capturedToken) {
                const runtimeToken = await extractBearerTokenFromRuntime(page);
                if (runtimeToken) {
                    capturedToken = runtimeToken;
                    tokenSource = tokenSource || 'runtime_keycloak_or_dataAuth';
                }
            }
            if (capturedToken) break;
            await sleep(SIAM_TOKEN_POLL_INTERVAL_MS);
        }

        if (!capturedToken) {
            await page.goto('https://siam.ub.ac.id/mahasiswa/presensi', { waitUntil: 'domcontentloaded' }).catch(() => null);
            await sleep(SHORT_WAIT_MS);
            const runtimeToken = await extractBearerTokenFromRuntime(page);
            if (runtimeToken) {
                capturedToken = runtimeToken;
                tokenSource = tokenSource || 'runtime_after_presensi_navigation';
            }
        }

        finalUiState = await getSiamUiState(page);
        console.log(
            `[INFO][SIAM][AUTH][${requestId}] attempt=${attempt} tokenCaptured=${Boolean(capturedToken)} tokenSource=${tokenSource || 'none'} tokenEndpointStatus=${tokenEndpointStatus || 'n/a'} accountEndpointStatus=${accountEndpointStatus || 'n/a'} url=${finalUiState.currentUrl}`
        );

        if (!capturedToken) {
            if (tokenEndpointStatus === 200 && accountEndpointStatus === 403) {
                throw new ServiceError(
                    'SIAM_AUTH_NOT_ESTABLISHED',
                    'SIAM login completed but account authorization did not establish a usable session.',
                    {
                        tokenEndpointStatus,
                        accountEndpointStatus,
                        currentUrl: finalUiState.currentUrl,
                        loginButtonVisible: finalUiState.loginButtonVisible
                    },
                    502
                );
            }

            throw new ServiceError(
                'SIAM_TOKEN_MISSING',
                'Failed to capture SIAM bearer token.',
                {
                    tokenEndpointStatus,
                    accountEndpointStatus,
                    currentUrl: finalUiState.currentUrl,
                    loginButtonVisible: finalUiState.loginButtonVisible
                },
                502
            );
        }

        return {
            token: capturedToken,
            source: tokenSource || 'unknown',
            tokenEndpointStatus,
            accountEndpointStatus,
            uiState: finalUiState
        };
    } finally {
        page.off('request', onRequest);
        page.off('response', onResponse);
    }
}

async function runWithSiamRetries(options) {
    const { requestId, endpoint, username, password, operation, shouldRetry } = options;
    const cooldownError = getSiamCooldownError();
    if (cooldownError) throw cooldownError;

    let lastError = null;

    for (let attempt = 1; attempt <= SIAM_AUTH_MAX_ATTEMPTS; attempt += 1) {
        let browser;
        try {
            browser = trackBrowser(await puppeteer.launch(createLaunchOptions()));
            const page = await browser.newPage();
            await prepareSiamPage(page);

            const auth = await getSiamAuth(page, username, password, { requestId, endpoint, attempt });
            const data = await operation({ page, token: auth.token, auth, attempt });

            registerSiamSuccess();
            return { data, auth, attempt };
        } catch (error) {
            lastError = normalizeError(error, 'SIAM_UPSTREAM_FAILURE', 502);
            registerSiamFailure(lastError.code);
            console.error(
                `[ERROR][SIAM][${endpoint}][${requestId}] attempt=${attempt} code=${lastError.code} message=${lastError.message}`
            );

            const canRetry = typeof shouldRetry === 'function' ? shouldRetry(lastError) : true;
            if (!canRetry) {
                throw lastError;
            }

            if (attempt < SIAM_AUTH_MAX_ATTEMPTS) {
                await sleep(retryDelayMs(attempt));
            }
        } finally {
            await closeBrowserSafely(browser, `[INFO][SIAM][${endpoint}][${requestId}]`);
        }
    }

    throw new ServiceError(
        'SIAM_AUTH_RETRY_EXHAUSTED',
        `SIAM auth failed after ${SIAM_AUTH_MAX_ATTEMPTS} attempts.`,
        {
            endpoint,
            attempts: SIAM_AUTH_MAX_ATTEMPTS,
            lastErrorCode: lastError?.code || 'UNKNOWN',
            lastErrorMessage: lastError?.message || 'Unknown error'
        },
        lastError?.statusCode || 502
    );
}



app.post('/get-cookies', async (req, res) => {
    const { username, password } = req.body;
    let browser;

    try {
        browser = trackBrowser(await puppeteer.launch(createLaunchOptions()));

        const page = await browser.newPage();
        await page.evaluateOnNewDocument(() => {
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
        });
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36');

        console.log('[INFO][BRONE] Opening Brone login page...');
        await page.goto('https://brone.ub.ac.id/login/index.php', { waitUntil: 'networkidle2' });

        console.log('[INFO][BRONE] Waiting for login form...');
        try {
            await page.waitForSelector('#username', { visible: true, timeout: 30000 });
        } catch (error) {
            await page.screenshot({ path: '/app/debug-error-brone.png', fullPage: true });
            throw new Error('Login form not found. Check debug-error-brone.png');
        }

        console.log('[INFO][BRONE] Filling credentials...');
        await page.type('#username', username, { delay: 30 });
        await page.type('#password', password, { delay: 30 });

        console.log('[INFO][BRONE] Clicking Sign In and waiting for redirect...');
        try {
            await Promise.all([
                page.waitForFunction("window.location.hostname === 'brone.ub.ac.id'", { timeout: 45000 }),
                page.click('#kc-login')
            ]);
            await new Promise(resolve => setTimeout(resolve, SHORT_WAIT_MS));
        } catch (error) {
            await page.screenshot({ path: '/app/debug-redirect-brone.png' });
            throw new Error('Redirect failed. Check debug-redirect-brone.png');
        }

        console.log('[INFO][BRONE] Collecting cookies and sesskey...');
        const cookies = await page.cookies();
        const cookieString = cookies.map(c => `${c.name}=${c.value}`).join('; ');

        const sesskey = await page.evaluate(() => {
            if (typeof M !== 'undefined' && M.cfg && M.cfg.sesskey) return M.cfg.sesskey;
            const logoutLink = document.querySelector('a[href*="logout.php?sesskey="]');
            return logoutLink ? new URL(logoutLink.href).searchParams.get('sesskey') : 'NOT_FOUND';
        });

        console.log('[INFO][BRONE] Cookies and sesskey fetched successfully.');

        res.json({ success: true, cookieString, sesskey });
    } catch (error) {
        console.error('[ERROR][BRONE]', error.message);
        res.status(500).json({ error: error.message });
    } finally {
        console.log('[INFO][BRONE] Closing browser session.');
        await closeBrowserSafely(browser, '[INFO][BRONE]');
    }
});





app.post('/get-siam-pengumuman', async (req, res) => {
    
    const { username, password, courses } = req.body; 
    let browser;

    try {
        browser = trackBrowser(await puppeteer.launch(createLaunchOptions()));

        const page = await browser.newPage();
        await page.evaluateOnNewDocument(() => {
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
        });
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36');

        let bearerToken = null;

        await page.setRequestInterception(true);
        page.on('request', (request) => {
            const headers = request.headers();
            if (headers['authorization'] && headers['authorization'].toLowerCase().includes('bearer')) {
                bearerToken = headers['authorization'];
            }
            request.continue();
        });

        console.log('[INFO][SIAM] Opening SIAM landing page...');
        await page.goto('https://siam.ub.ac.id', { waitUntil: 'networkidle2' });

        console.log('[INFO][SIAM] Clicking LOGIN UB button...');
        try {
            await page.waitForSelector('button.btn-primary', { visible: true, timeout: 15000 });
            await page.click('button.btn-primary');
        } catch (error) {
            throw new Error('Failed to click LOGIN UB button.');
        }

        console.log('[INFO][SIAM] Filling SSO credentials...');
        await page.waitForSelector('#username', { visible: true, timeout: 30000 });
        await page.type('#username', username, { delay: 30 });
        await page.type('#password', password, { delay: 30 });

        console.log('[INFO][SIAM] Logging in and waiting for redirect...');
        await Promise.all([
            page.waitForFunction("window.location.hostname === 'siam.ub.ac.id'", { timeout: 45000 }),
            page.click('#kc-login')
        ]);

        await new Promise(resolve => setTimeout(resolve, SHORT_WAIT_MS));

        console.log('[INFO][SIAM] Triggering token capture from perkuliahan page...');
        await page.goto('https://siam.ub.ac.id/mahasiswa/perkuliahan', { waitUntil: 'domcontentloaded' });
        await new Promise(resolve => setTimeout(resolve, SHORT_WAIT_MS));

        if (!bearerToken) {
            throw new Error('Failed to capture Bearer token.');
        }

        console.log('[INFO][SIAM] Bearer token captured. Starting announcement fetch workflow...');
        const hasilPanen = [];

        
        if (courses && courses.length > 0) {
            const hasilPerMatkul = await page.evaluate(async (courseList, token) => {
                const baseUrl = 'https://api.ub.ac.id/siam/mahasiswa/getPengumumanKelas?tahun=2025&is_ganjil=0&is_pendek=0';

                const tasks = courseList.map(async (matkul) => {
                    const url = `${baseUrl}&kelas=${encodeURIComponent(matkul.kelas)}&kode_mk=${encodeURIComponent(matkul.kode_mk)}`;
                    try {
                        const response = await fetch(url, {
                            method: 'GET',
                            headers: {
                                'Authorization': token,
                                'Accept': 'application/json'
                            }
                        });
                        const data = await response.json();
                        return {
                            matkul,
                            data: Array.isArray(data) ? data : []
                        };
                    } catch (error) {
                        return {
                            matkul,
                            error: error.message,
                            data: []
                        };
                    }
                });

                return Promise.all(tasks);
            }, courses, bearerToken);

            const batasHariMundur = 1;
            const hariIni = new Date();
            hariIni.setHours(0, 0, 0, 0);

            for (const result of hasilPerMatkul) {
                const { matkul, data, error } = result;
                console.log(`[INFO][SIAM] Checking course: ${matkul.nama} (${matkul.kode_mk}-${matkul.kelas})`);

                if (error) {
                    console.error(`[ERROR][SIAM] Failed fetching announcements for ${matkul.nama}:`, error);
                    continue;
                }

                const pengumumanBaru = data.filter(item => {
                    if (!item.TGL_AWAL) return false;

                    const tglAwal = new Date(item.TGL_AWAL);
                    tglAwal.setHours(0, 0, 0, 0);

                    const selisihHari = (hariIni - tglAwal) / (1000 * 60 * 60 * 24);
                    return selisihHari <= batasHariMundur;
                });

                if (pengumumanBaru.length > 0) {
                    hasilPanen.push({
                        matkul: matkul.nama,
                        kode: matkul.kode_mk,
                        kelas: matkul.kelas,
                        daftar_pengumuman: pengumumanBaru.map(p => ({
                            tanggal: p.TGL_AWAL,
                            isi: p.PENGUMUMAN
                        }))
                    });
                }
            }
        }

        console.log('[INFO][SIAM] Announcement fetch workflow completed.');
        res.json({ success: true, data: hasilPanen });

    } catch (error) {
        console.error('[ERROR][SIAM]', error.message);
        res.status(500).json({ error: error.message });
    } finally {
        console.log('[INFO][SIAM] Closing browser session.');
        await closeBrowserSafely(browser, '[INFO][SIAM]');
    }
});




app.post('/get-siam-presensi', async (req, res) => {
    const { username, password } = req.body;
    const requestId = createRequestId('presensi-get');
    let browser;

    try {
        if (!username || !password) {
            throw new ServiceError(
                'SIAM_AUTH_INVALID_PAYLOAD',
                'username and password are required.',
                { username: Boolean(username), password: Boolean(password) },
                400
            );
        }

        browser = trackBrowser(await puppeteer.launch(createLaunchOptions()));
        const page = await browser.newPage();
        await prepareSiamPage(page);

        let bearerToken = null;
        await page.setRequestInterception(true);
        page.on('request', (request) => {
            const headers = request.headers();
            const authHeader = headers.authorization || headers.Authorization;
            if (!bearerToken && typeof authHeader === 'string' && /^bearer\s+/i.test(authHeader)) {
                bearerToken = authHeader;
            }
            if (typeof request.isInterceptResolutionHandled === 'function' && request.isInterceptResolutionHandled()) {
                return;
            }
            request.continue().catch((interceptError) => {
                console.warn(
                    `[WARN][PRESENSI][get-siam-presensi][${requestId}] requestContinueFailed=${interceptError.message}`
                );
            });
        });

        console.log(`[INFO][PRESENSI][get-siam-presensi][${requestId}] Opening SIAM landing page...`);
        await page.goto('https://siam.ub.ac.id', { waitUntil: 'networkidle2' });

        console.log(`[INFO][PRESENSI][get-siam-presensi][${requestId}] Clicking LOGIN UB button...`);
        await page.waitForSelector('button.btn-primary', { visible: true, timeout: 15000 });
        await page.click('button.btn-primary');

        console.log(`[INFO][PRESENSI][get-siam-presensi][${requestId}] Filling SSO credentials...`);
        await page.waitForSelector('#username', { visible: true, timeout: 30000 });
        await page.type('#username', username, { delay: 20 });
        await page.type('#password', password, { delay: 20 });

        console.log(`[INFO][PRESENSI][get-siam-presensi][${requestId}] Logging in and waiting for redirect...`);
        await Promise.all([
            page.waitForFunction("window.location.hostname === 'siam.ub.ac.id'", { timeout: 45000 }),
            page.click('#kc-login')
        ]);

        await sleep(SHORT_WAIT_MS);

        console.log(`[INFO][PRESENSI][get-siam-presensi][${requestId}] Triggering token capture from perkuliahan page...`);
        await page.goto('https://siam.ub.ac.id/mahasiswa/perkuliahan', { waitUntil: 'domcontentloaded' });
        await sleep(SHORT_WAIT_MS);

        if (!bearerToken) {
            throw new ServiceError(
                'SIAM_TOKEN_MISSING',
                'Failed to capture Bearer token.',
                { endpoint: 'get-siam-presensi' },
                502
            );
        }

        const response = await page.evaluate(async (token) => {
            const apiResponse = await fetch('https://api.ub.ac.id/siam/mahasiswa/getPresensiPerkuliahan?is_aktif=1', {
                method: 'GET',
                headers: {
                    Authorization: token,
                    Accept: 'application/json, text/plain, */*'
                }
            });
            const bodyText = await apiResponse.text();
            let bodyJson = null;
            try {
                bodyJson = bodyText ? JSON.parse(bodyText) : null;
            } catch {
                bodyJson = null;
            }
            return {
                ok: apiResponse.ok,
                status: apiResponse.status,
                statusText: apiResponse.statusText,
                bodyJson,
                bodyText
            };
        }, bearerToken);

        if (!response.ok) {
            throw new ServiceError(
                'SIAM_PRESENSI_FETCH_FAILED',
                `Failed to fetch SIAM attendance data (HTTP ${response.status}).`,
                {
                    endpoint: 'get-siam-presensi',
                    status: response.status,
                    statusText: response.statusText,
                    responseBody: response.bodyJson || response.bodyText
                },
                response.status >= 500 ? 502 : 400
            );
        }

        const dataPresensi = Array.isArray(response.bodyJson)
            ? response.bodyJson
            : (response.bodyJson ?? []);

        console.log(
            `[INFO][PRESENSI][get-siam-presensi][${requestId}] Attendance data fetched successfully. activeCount=${Array.isArray(dataPresensi) ? dataPresensi.length : 0}`
        );
        res.json({ success: true, requestId, data: dataPresensi });
    } catch (error) {
        const normalized = normalizeError(error, 'SIAM_PRESENSI_FETCH_FAILED', 502);
        console.error(
            `[ERROR][PRESENSI][get-siam-presensi][${requestId}] code=${normalized.code} message=${normalized.message}`
        );
        sendError(res, requestId, normalized, 502);
    } finally {
        await closeBrowserSafely(browser, `[INFO][PRESENSI][get-siam-presensi][${requestId}]`);
    }
});

// ==========================================
// 4. ENDPOINT SIAM (SUBMIT PRESENSI / ABSEN)
// ==========================================
app.post('/submit-siam-presensi', async (req, res) => {
    const { username, password, kode_materi, kode_absensi, is_daring } = req.body;
    const requestId = createRequestId('presensi-submit');

    try {
        if (!kode_materi || !kode_absensi) {
            throw new ServiceError(
                'SIAM_PRESENSI_INVALID_PAYLOAD',
                'kode_materi and kode_absensi are required.',
                { kode_materi: Boolean(kode_materi), kode_absensi: Boolean(kode_absensi) },
                400
            );
        }

        const result = await runWithSiamRetries({
            requestId,
            endpoint: 'submit-siam-presensi',
            username,
            password,
            shouldRetry: (error) => {
                if (error instanceof ServiceError && error.statusCode < 500) return false;
                return isLikelyTransientNetworkError(error) || error.statusCode >= 500;
            },
            operation: async ({ page, token, auth, attempt }) => {
                await warmupSiamPresensiPage(page, { endpoint: 'submit-siam-presensi', requestId, attempt });

                const response = await page.evaluate(async (bearer, materi, absensi, daring) => {
                    const formData = new FormData();
                    formData.append('kode_materi', materi);
                    formData.append('kode_absensi', absensi);
                    formData.append('keterangan', '');
                    formData.append('is_daring', String(daring ?? ''));
                    formData.append('catatan', '');

                    const apiResponse = await fetch('https://api.ub.ac.id/siam/mahasiswa/prosesPresensiPerkuliahan', {
                        method: 'POST',
                        headers: {
                            Authorization: bearer,
                            Accept: 'application/json, text/plain, */*'
                        },
                        body: formData
                    });
                    const bodyText = await apiResponse.text();
                    let bodyJson = null;
                    try {
                        bodyJson = bodyText ? JSON.parse(bodyText) : null;
                    } catch {
                        bodyJson = null;
                    }
                    return {
                        ok: apiResponse.ok,
                        status: apiResponse.status,
                        statusText: apiResponse.statusText,
                        bodyText,
                        bodyJson
                    };
                }, token, kode_materi, kode_absensi, is_daring);

                console.log(
                    `[INFO][PRESENSI][submit-siam-presensi][${requestId}] attempt=${attempt} authSource=${auth.source} status=${response.status}`
                );

                if (!response.ok) {
                    throw new ServiceError(
                        'SIAM_PRESENSI_SUBMIT_FAILED',
                        `Failed to submit SIAM attendance (HTTP ${response.status}).`,
                        {
                            status: response.status,
                            statusText: response.statusText,
                            authSource: auth.source,
                            kode_materi,
                            kode_absensi,
                            responseBody: response.bodyJson || response.bodyText
                        },
                        response.status >= 500 ? 502 : 400
                    );
                }

                return response.bodyJson || response.bodyText;
            }
        });

        console.log(`[INFO][PRESENSI][submit-siam-presensi][${requestId}] Attendance submission completed.`);
        res.json({ success: true, requestId, data: result.data });
    } catch (error) {
        const normalized = normalizeError(error, 'SIAM_PRESENSI_SUBMIT_FAILED', 502);
        console.error(
            `[ERROR][PRESENSI][submit-siam-presensi][${requestId}] code=${normalized.code} message=${normalized.message}`
        );
        sendError(res, requestId, normalized, 502);
    }
});

const PORT = 3000;
server = app.listen(PORT, () => console.log(`[INFO][BOOT] Brone Auth Service is running on port ${PORT}`));

const fs = require('fs/promises');
const os = require('os');
const path = require('path');

const DEFAULT_PROFILE_ROOT = path.join(os.tmpdir(), 'brone-puppeteer');

function positiveInteger(value, fallback) {
    const parsed = Number(value);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

class BrowserSlotPool {
    constructor(limit = 1, queueTimeoutMs = 60000) {
        this.limit = positiveInteger(limit, 1);
        this.queueTimeoutMs = positiveInteger(queueTimeoutMs, 60000);
        this.active = 0;
        this.queue = [];
    }

    acquire() {
        if (this.active < this.limit) {
            this.active += 1;
            return Promise.resolve(this.createRelease());
        }

        return new Promise((resolve, reject) => {
            const entry = { resolve, reject, timer: null };
            entry.timer = setTimeout(() => {
                const index = this.queue.indexOf(entry);
                if (index >= 0) this.queue.splice(index, 1);
                reject(new Error(`Browser queue timed out after ${this.queueTimeoutMs}ms.`));
            }, this.queueTimeoutMs);
            this.queue.push(entry);
        });
    }

    createRelease() {
        let released = false;
        return () => {
            if (released) return;
            released = true;

            const next = this.queue.shift();
            if (next) {
                clearTimeout(next.timer);
                next.resolve(this.createRelease());
                return;
            }

            this.active = Math.max(0, this.active - 1);
        };
    }

    status() {
        return { active: this.active, queued: this.queue.length, limit: this.limit };
    }
}

function isOwnedProfile(profileDir, profileRoot) {
    const resolvedRoot = path.resolve(profileRoot);
    const relative = path.relative(resolvedRoot, path.resolve(profileDir));
    return relative.startsWith('profile-') && !relative.includes(path.sep);
}

async function createProfileDir(profileRoot = DEFAULT_PROFILE_ROOT) {
    await fs.mkdir(profileRoot, { recursive: true, mode: 0o700 });
    return fs.mkdtemp(path.join(profileRoot, 'profile-'));
}

async function removeProfileDir(profileDir, profileRoot = DEFAULT_PROFILE_ROOT) {
    if (!profileDir) return;
    if (!isOwnedProfile(profileDir, profileRoot)) {
        throw new Error(`Refusing to remove a profile outside ${profileRoot}.`);
    }
    await fs.rm(profileDir, { recursive: true, force: true, maxRetries: 3, retryDelay: 200 });
}

async function removeRuntimeArtifacts(runtimeDir) {
    if (!runtimeDir) return;
    const entries = await fs.readdir(runtimeDir, { withFileTypes: true }).catch((error) => {
        if (error.code === 'ENOENT') return [];
        throw error;
    });
    await Promise.all(entries
        .filter((entry) => entry.name.startsWith('com.google.Chrome.'))
        .map((entry) => fs.rm(path.join(runtimeDir, entry.name), {
            recursive: true,
            force: true,
            maxRetries: 3,
            retryDelay: 200
        })));
}

async function createBrowserSession({ launch, createLaunchOptions, pool, profileRoot = DEFAULT_PROFILE_ROOT, runtimeDir }) {
    if (typeof launch !== 'function' || typeof createLaunchOptions !== 'function') {
        throw new Error('launch and createLaunchOptions are required.');
    }

    const release = await pool.acquire();
    let profileDir;
    try {
        if (runtimeDir) await fs.mkdir(runtimeDir, { recursive: true, mode: 0o700 });
        profileDir = await createProfileDir(profileRoot);
        const browser = await launch(createLaunchOptions(profileDir));
        return { browser, profileDir, profileRoot, runtimeDir, release };
    } catch (error) {
        try {
            await removeProfileDir(profileDir, profileRoot);
            await removeRuntimeArtifacts(runtimeDir);
        } finally {
            release();
        }
        throw error;
    }
}

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

async function closeBrowserSession(session, { context = '[BROWSER]', closeTimeoutMs = 10000, logger = console } = {}) {
    if (!session) return;

    try {
        if (session.browser) {
            let timeout;
            try {
                await Promise.race([
                    session.browser.close(),
                    new Promise((_, reject) => {
                        timeout = setTimeout(() => reject(new Error(`Browser close timed out after ${closeTimeoutMs}ms.`)), closeTimeoutMs);
                    })
                ]);
            } finally {
                clearTimeout(timeout);
            }
        }
    } catch (error) {
        logger.error(`${context} Failed to close browser cleanly:`, error.message);
        const processHandle = session.browser?.process?.();
        if (processHandle?.pid) {
            try {
                process.kill(processHandle.pid, 'SIGKILL');
                await sleep(250);
            } catch (killError) {
                logger.error(`${context} Failed to kill browser process:`, killError.message);
            }
        }
    } finally {
        try {
            await removeProfileDir(session.profileDir, session.profileRoot);
            await removeRuntimeArtifacts(session.runtimeDir);
        } catch (cleanupError) {
            logger.error(`${context} Failed to remove temporary profile:`, cleanupError.message);
        }
        session.release?.();
    }
}

module.exports = {
    BrowserSlotPool,
    DEFAULT_PROFILE_ROOT,
    closeBrowserSession,
    createBrowserSession,
    createProfileDir,
    removeProfileDir,
    removeRuntimeArtifacts
};

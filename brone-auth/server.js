const express = require('express');
const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');

puppeteer.use(StealthPlugin());

const app = express();
app.use(express.json());

async function getSiamAuth(page, username, password) {
    let token = null;
    await page.setRequestInterception(true);
    page.on('request', (request) => {
        const headers = request.headers();
        if (headers['authorization']?.toLowerCase().includes('bearer')) {
            token = headers['authorization'];
        }
        request.continue();
    });

    await page.goto('https://siam.ub.ac.id', { waitUntil: 'networkidle2' });
    await page.waitForSelector('button.btn-primary', { visible: true, timeout: 15000 });
    await page.click('button.btn-primary');

    await page.waitForSelector('#username', { visible: true, timeout: 30000 });
    await page.type('#username', username, { delay: 50 });
    await page.type('#password', password, { delay: 50 });
    
    await Promise.all([
        page.waitForFunction("window.location.hostname === 'siam.ub.ac.id'", { timeout: 45000 }),
        page.click('#kc-login')
    ]);
    await new Promise(r => setTimeout(r, 5000));
    return token;
}



app.post('/get-cookies', async (req, res) => {
    const { username, password } = req.body;
    let browser;

    try {
        browser = await puppeteer.launch({
            headless: 'new',
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled'
            ]
        });

        const page = await browser.newPage();
        await page.evaluateOnNewDocument(() => {
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
        });
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36');

        console.log("LOG [BRONE]: Menuju Brone...");
        await page.goto('https://brone.ub.ac.id/login/index.php', { waitUntil: 'networkidle2' });

        console.log("LOG [BRONE]: Menunggu form login...");
        try {
            await page.waitForSelector('#username', { visible: true, timeout: 30000 });
        } catch (error) {
            await page.screenshot({ path: '/app/debug-error-brone.png', fullPage: true });
            throw new Error("Gagal nemu form login. Cek debug-error-brone.png");
        }

        console.log("LOG [BRONE]: Mengisi kredensial...");
        await page.type('#username', username, { delay: 100 });
        await page.type('#password', password, { delay: 120 });
        await new Promise(resolve => setTimeout(resolve, 1500));

        console.log("LOG [BRONE]: Klik Sign In...");
        try {
            await Promise.all([
                page.waitForFunction("window.location.hostname === 'brone.ub.ac.id'", { timeout: 45000 }),
                page.click('#kc-login')
            ]);
            await new Promise(resolve => setTimeout(resolve, 3000));
        } catch (error) {
            await page.screenshot({ path: '/app/debug-redirect-brone.png' });
            throw new Error("Gagal redirect. Cek debug-redirect-brone.png");
        }

        console.log("LOG [BRONE]: Mengambil cookie dan sesskey...");
        const cookies = await page.cookies();
        const cookieString = cookies.map(c => `${c.name}=${c.value}`).join('; ');

        const sesskey = await page.evaluate(() => {
            if (typeof M !== 'undefined' && M.cfg && M.cfg.sesskey) return M.cfg.sesskey;
            const logoutLink = document.querySelector('a[href*="logout.php?sesskey="]');
            return logoutLink ? new URL(logoutLink.href).searchParams.get('sesskey') : "TIDAK_KETEMU";
        });

        res.json({ success: true, cookieString, sesskey });
    } catch (error) {
        console.error("LOG ERROR [BRONE]:", error.message);
        res.status(500).json({ error: error.message });
    } finally {
        if (browser) await browser.close();
    }
});





app.post('/get-siam-pengumuman', async (req, res) => {
    
    const { username, password, courses } = req.body; 
    let browser;

    try {
        browser = await puppeteer.launch({
            headless: 'new',
            args: [
                '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled'
            ]
        });

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

        console.log("LOG [SIAM]: Menuju Landing Page SIAM...");
        await page.goto('https://siam.ub.ac.id', { waitUntil: 'networkidle2' });

        console.log("LOG [SIAM]: Klik LOGIN UB...");
        try {
            await page.waitForSelector('button.btn-primary', { visible: true, timeout: 15000 });
            await page.click('button.btn-primary');
        } catch (error) {
            throw new Error("Gagal klik tombol LOGIN UB.");
        }

        console.log("LOG [SIAM]: Mengisi kredensial SSO...");
        await page.waitForSelector('#username', { visible: true, timeout: 30000 });
        await page.type('#username', username, { delay: 100 });
        await page.type('#password', password, { delay: 120 });
        await new Promise(resolve => setTimeout(resolve, 1500));

        console.log("LOG [SIAM]: Login dan tunggu redirect...");
        await Promise.all([
            page.waitForFunction("window.location.hostname === 'siam.ub.ac.id'", { timeout: 45000 }),
            page.click('#kc-login')
        ]);
        
        await new Promise(resolve => setTimeout(resolve, 5000));

        console.log("LOG [SIAM]: Mancing Token di halaman jadwal...");
        await page.goto('https://siam.ub.ac.id/mahasiswa/perkuliahan', { waitUntil: 'networkidle2' });
        await new Promise(resolve => setTimeout(resolve, 3000));

        if (!bearerToken) {
            throw new Error("Gagal menyadap Bearer Token.");
        }

        console.log("LOG [SIAM]: Token dapet! Mulai operasi panen API dari dalam browser...");
        const hasilPanen = [];

        
        if (courses && courses.length > 0) {
            for (const matkul of courses) {
                const apiUrl = `https://api.ub.ac.id/siam/mahasiswa/getPengumumanKelas?tahun=2025&is_ganjil=0&is_pendek=0&kelas=${matkul.kelas}&kode_mk=${matkul.kode_mk}`;
                
                console.log(`Mengecek: ${matkul.nama}...`);
                
try {
                    
                    const dataPengumuman = await page.evaluate(async (url, token) => {
                        const response = await fetch(url, {
                            method: 'GET',
                            headers: {
                                'Authorization': token,
                                'Accept': 'application/json'
                            }
                        });
                        return await response.json();
                    }, apiUrl, bearerToken);

                    
                    const batasHariMundur = 3; 
                    const hariIni = new Date();
                    hariIni.setHours(0, 0, 0, 0); 

                    const pengumumanBaru = dataPengumuman.filter(item => {
                        if (!item.TGL_AWAL) return false; 
                        
                        const tglAwal = new Date(item.TGL_AWAL);
                        tglAwal.setHours(0, 0, 0, 0);
                        
                        
                        const selisihHari = (hariIni - tglAwal) / (1000 * 60 * 60 * 24);
                        
                        
                        
                        
                        return selisihHari <= batasHariMundur;
                    });

                    
                    if (pengumumanBaru.length > 0) {
                        
                        const listPengumumanBeres = pengumumanBaru.map(p => ({
                            tanggal: p.TGL_AWAL,
                            isi: p.PENGUMUMAN
                        }));

                        hasilPanen.push({
                            matkul: matkul.nama,
                            kode: matkul.kode_mk,
                            kelas: matkul.kelas,
                            daftar_pengumuman: listPengumumanBeres
                        });
                    }

                    
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    
                } catch (err) {
                    console.log(`Gagal fetch matkul ${matkul.nama}:`, err.message);
                }
            }
        }

        console.log("LOG [SIAM]: Operasi Panen Selesai!");
        res.json({ success: true, data: hasilPanen });

    } catch (error) {
        console.error("LOG ERROR [SIAM]:", error.message);
        res.status(500).json({ error: error.message });
    } finally {
        if (browser) await browser.close();
    }
});




app.post('/get-siam-presensi', async (req, res) => {
    const { username, password } = req.body;
    let browser;
    try {
        browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox', '--disable-setuid-sandbox'] });
        const page = await browser.newPage();
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36');

        const bearerToken = await getSiamAuth(page, username, password);
        
        console.log("LOG [PRESENSI]: Menuju halaman presensi...");
        await page.goto('https://siam.ub.ac.id/mahasiswa/presensi', { waitUntil: 'networkidle2' });
        await new Promise(r => setTimeout(r, 2000));

        if (!bearerToken) throw new Error("Gagal sadap token presensi.");

        const dataPresensi = await page.evaluate(async (token) => {
            const res = await fetch('https://api.ub.ac.id/siam/mahasiswa/getPresensiPerkuliahan?is_aktif=1', {
                headers: { 'Authorization': token, 'Accept': 'application/json' }
            });
            return await res.json();
        }, bearerToken);

        res.json({ success: true, data: dataPresensi });
    } catch (e) {
        res.status(500).json({ error: e.message });
    } finally {
        if (browser) await browser.close();
    }
});

const PORT = 3000;
app.listen(PORT, () => console.log(`Brone Auth Service running on port ${PORT}`));
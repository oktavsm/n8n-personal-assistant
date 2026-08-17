const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const {
    BrowserSlotPool,
    closeBrowserSession,
    createBrowserSession
} = require('./browser-session');

async function temporaryRoot() {
    return fs.mkdtemp(path.join(os.tmpdir(), 'brone-browser-session-test-'));
}

test('removes its profile after a successful browser session', async (t) => {
    const profileRoot = await temporaryRoot();
    const runtimeDir = path.join(profileRoot, 'runtime');
    t.after(() => fs.rm(profileRoot, { recursive: true, force: true }));
    let launchOptions;

    const session = await createBrowserSession({
        profileRoot,
        runtimeDir,
        pool: new BrowserSlotPool(1),
        createLaunchOptions: (profileDir) => ({ userDataDir: profileDir }),
        launch: async (options) => {
            launchOptions = options;
            return { close: async () => {} };
        }
    });

    assert.equal(launchOptions.userDataDir, session.profileDir);
    await fs.access(session.profileDir);
    await fs.mkdir(path.join(runtimeDir, 'com.google.Chrome.test'));
    await closeBrowserSession(session, { logger: { error: () => {} } });
    await assert.rejects(fs.access(session.profileDir));
    await assert.rejects(fs.access(path.join(runtimeDir, 'com.google.Chrome.test')));
});

test('removes its profile and releases the slot when browser launch fails', async (t) => {
    const profileRoot = await temporaryRoot();
    t.after(() => fs.rm(profileRoot, { recursive: true, force: true }));
    const pool = new BrowserSlotPool(1);

    await assert.rejects(
        createBrowserSession({
            profileRoot,
            pool,
            createLaunchOptions: (profileDir) => ({ userDataDir: profileDir }),
            launch: async () => { throw new Error('launch failed'); }
        }),
        /launch failed/
    );

    assert.deepEqual(await fs.readdir(profileRoot), []);
    assert.deepEqual(pool.status(), { active: 0, queued: 0, limit: 1 });
});

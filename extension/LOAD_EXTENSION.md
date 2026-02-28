# How to Run ContractLens on Your Laptop

The extension talks to a **hosted API** (no need to run the backend yourself). Follow one of the options below.

---

## Option A: You got a zip from your friend (easiest)

If your friend sent you a **zip of the built extension** (e.g. `contractlens-extension.zip`):

1. **Unzip** it to a folder (e.g. `ContractLens` on your Desktop).
2. Open **Chrome** → go to `chrome://extensions/`.
3. Turn **Developer mode** ON (top-right toggle).
4. Click **Load unpacked**.
5. Choose the **unzipped folder** (the one that contains `manifest.json`).
6. The ContractLens icon should appear in the toolbar. Click it and use the side panel to analyze pages.

Done. The extension is already configured to use the hosted API.

---

## Option B: You have the project (clone or copy)

If you have the full **Hack_the_east** project (or just the `extension` folder):

1. **Terminal:** go into the extension folder and install dependencies (one-time):
   ```bash
   cd extension
   npm install
   ```

2. **Build** the extension using the **hosted API URL** (your friend will give you this; it looks like `https://xxxx.execute-api.us-east-1.amazonaws.com`):
   ```bash
   VITE_API_BASE=https://YOUR_API_URL_HERE npm run build
   ```
   Example:
   ```bash
   VITE_API_BASE=https://gdpsa4vsj6.execute-api.us-east-1.amazonaws.com npm run build
   ```

3. In Chrome go to **`chrome://extensions/`** → turn **Developer mode** ON → **Load unpacked** → select the **`extension/dist`** folder.

4. Use the extension from the toolbar.

---

## Quick reference

| Step              | What to do |
|-------------------|------------|
| Load in Chrome    | `chrome://extensions/` → Developer mode ON → Load unpacked → select folder with `manifest.json` |
| Folder to select  | **Option A:** the unzipped folder your friend sent. **Option B:** `extension/dist` after building. |
| If something breaks | Make sure you selected the folder that **contains** `manifest.json`, not a parent folder. |

No backend or server setup needed — the API is already hosted.

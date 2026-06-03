# Email: Tipout install instructions for parents

> Draft to send. The download link works once you've published the first release
> (`git tag v0.2.0 && git push origin v0.2.0`). Subject + body below.

---

**Subject:** New, easier way to run the tip-out (no more GitHub!)

Hi Mom & Dad,

I made the tip-out tool way easier to set up. You only have to do this **once**, and there's no GitHub and no installing Python anymore. Here's all of it:

**Step 1 — Download one file**

Click this link and save the file (it's called `tipout-plugin.zip`):
👉 https://github.com/CooperReal/tip-out/releases/latest

On that page, under "Assets," click **tipout-plugin.zip** to download it. Just remember which folder it saved to (usually your "Downloads" folder).

**Step 2 — Add it to Claude**

1. Open the **Claude** app and click the **Cowork** tab.
2. On the left, click **Customize**.
3. Click **Browse plugins**.
4. Choose the option to **upload a plugin file**, and pick the `tipout-plugin.zip` you just downloaded.

That's it — it's installed.

**Step 3 — Use it**

Just talk to Claude like normal. For example, drag in your POS file and say:

> "Run the tip-out for the pay period starting January 12."

The very first time, Claude will set everything up by itself (it downloads the calculator and creates a "Tipout" folder in your Documents). You don't have to do anything but answer its questions about any new names.

**When I send you an update**

You'll never have to re-download or reinstall. When I make a change, just open Claude and say:

> "update tipout"

It'll grab the newest version and tell you what changed. Done.

If anything looks confusing, call me and we'll do it together — but I think you'll find it's just those few clicks one time.

Love,
Cooper

---

## Note to self (not part of the email)

- The link points to the **latest release** page, so it always gives the newest plugin. It only works after the first release is published.
- If Claude says it can't run commands, the operator needs **code execution / Bash enabled** in Cowork settings — walk them through enabling it once.
- A plugin re-upload is only needed if the *skill instructions* themselves change. Pure calculation changes ship through "update tipout" with no reinstall.

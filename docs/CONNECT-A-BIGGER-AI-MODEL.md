# How to give the tool a smarter AI brain (super simple guide)

This guide shows you how to download a **more powerful AI model** and connect it to the
Schedule Analysis tool. It is written so that **anyone can follow it**, even if you have
never used a computer like this before. Take it one step at a time. You cannot break
anything by following these steps.

---

## First, the two things you need to know

**1. What is an "AI model"?**
Think of it like a brain you plug into the tool. The tool comes ready to use a *small*
brain. A **bigger** brain can read your schedule and explain it more clearly — but it is
slower and needs a stronger computer. This guide helps you swap the small brain for a
bigger one.

**2. Is this safe? Will my schedule leak onto the internet?**
No. Your schedule **never** leaves your computer. The tool is built to keep everything
private (this is a hard rule the program enforces by itself).

The **one and only** time you use the internet is to *download* the brain — exactly like
downloading an app or a game. Once the brain is downloaded, it lives on your computer. From
then on, the tool talks to it **only inside your own machine**. You could even unplug the
internet and it would still work.

---

## Step 1 — Install the helper program called "Ollama" (you only do this once)

"Ollama" (say it: *oh-LAH-mah*) is a free helper program that holds the AI brain and lets
the tool talk to it. The tool needs Ollama to be installed.

1. Open your internet browser (Chrome, Edge, Safari — whatever you normally use).
2. Go to this website by typing it in the top bar and pressing **Enter**:

   **https://ollama.com/download**

3. Click the big button for your kind of computer:
   - **Windows** if your computer is a Windows PC.
   - **macOS** if it is an Apple Mac.
4. A file will download. When it finishes, **double-click it** and click **Next / Install /
   Open** until it says it is done. (If it asks for your password, that is normal — type the
   password you use to log into your computer.)
5. That's it. Ollama is now installed. You usually never have to open it again — the
   Schedule tool turns it on automatically.

> 💡 You only ever do Step 1 **once**. After this, skip straight to Step 2 whenever you want
> a new brain.

---

## Step 2 — Open the "typing window" (called a Terminal)

To download a brain we type one short line into a special window. It is just a window where
you type commands instead of clicking buttons. Don't worry — you only type one line.

**On Windows:**
1. Click the **Start** button (the Windows logo, usually bottom-left).
2. Type the word: `terminal`
3. Click the app called **Terminal** (or **Command Prompt** — either is fine) when it
   appears.

**On a Mac:**
1. Press the **Command (⌘)** key and the **Spacebar** at the same time. A little search box
   opens.
2. Type the word: `terminal`
3. Press **Enter**. A plain window opens.

A window with a blinking cursor appears. This is the typing window. Leave it open for the
next step.

---

## Step 3 — Pick which brain to download

Bigger brains are smarter but need a stronger computer (more "memory", also called **RAM**).
Use this simple table. **If you are not sure, start with the first row** — it is a safe,
solid upgrade for most computers.

| Your computer's memory (RAM) | Brain to choose (copy this exact name) | What it's like |
|------------------------------|----------------------------------------|----------------|
| 8 GB (a basic laptop)        | `llama3.2:3b`                          | Small and quick. Good if your computer is older. |
| 16 GB (a normal modern laptop) | `llama3.1:8b`                        | The tool's standard brain — balanced and reliable. |
| 16–32 GB (a strong laptop)   | `qwen2.5:14b`                          | Noticeably smarter. A great upgrade. |
| 32 GB or more / gaming PC    | `qwen2.5:32b`                          | Very smart. Slower, but excellent answers. |
| 64 GB or more / workstation  | `llama3.1:70b`                         | The most powerful. Best answers, but slow on a normal computer. |

**How do I find out how much memory (RAM) my computer has?**
- **Windows:** Click Start, type `About your PC`, press Enter, and look for the line that
  says **"Installed RAM"**.
- **Mac:** Click the **Apple logo** (top-left) → **About This Mac** → look at **"Memory"**.

> 💡 A bigger brain is always smarter but always slower. If answers feel too slow, come back
> and pick the row above your current one (a smaller brain). You can have several brains
> downloaded and switch between them anytime.

---

## Step 4 — Download the brain (type one line)

1. Go back to the typing window (Terminal) from Step 2.
2. Type the word `ollama pull` then a space, then the brain name you chose from the table.
   For example, to get the smarter 14b brain you would type **exactly** this:

   ```
   ollama pull qwen2.5:14b
   ```

   (Swap `qwen2.5:14b` for whichever name you picked.)
3. Press **Enter**.
4. **Wait.** The brain is a big download (it can be several gigabytes, like downloading a
   long movie). You will see a progress bar filling up. This can take a few minutes to
   half an hour depending on your internet. Leave the window open and let it finish.
5. When it is done it will say **`success`**. The brain is now on your computer forever. You
   can close the typing window.

> 😟 **If it says "ollama: command not found" or "not recognized":** Ollama from Step 1
> didn't finish installing, or your computer needs a restart. Restart your computer, then
> try Step 4 again.

---

## Step 5 — Tell the tool to use the new brain

Now we point the Schedule tool at the brain you just downloaded.

1. Open the Schedule Analysis tool the way you normally do (it opens in your web browser).
2. Near the top of the page, click the link that says **"AI Settings"**.
3. On the AI Settings page, find the line that says **Backend**. Make sure it is set to
   **"Ollama (local)"**.
4. Find the line that says **Model**. Click the dropdown box and **choose the brain you
   just downloaded** (for example, `qwen2.5:14b`). It will appear in the list once it has
   finished downloading.
5. *(Only if you picked a very big brain like `llama3.1:70b`)* Find the box called
   **"Generation timeout (seconds)"** and type a bigger number, like `900`. This just gives
   the big brain extra time to think so it doesn't get cut off.
6. Click the **Save** button.

You should now see a green message that says **"Local AI is ON"**. 🎉 That means the new,
smarter brain is connected and working. The tool's written explanations will now be richer.

---

## If something doesn't work — quick fixes

- **The page says "Local AI is OFF" in red.**
  Wait about 10 seconds and **reload the page** (press the reload arrow in your browser, or
  press **F5**). The tool starts Ollama for you, and it sometimes needs a moment the first
  time.

- **The red message says my model "isn't installed".**
  The download in Step 4 hasn't finished, or the name is slightly different. Open the
  Model dropdown and pick a name that is actually in the list. Whatever is in that list is
  ready to use.

- **Answers are very slow.**
  You picked a brain that is a bit big for your computer. Go back to Step 3, pick the row
  *above* yours (a smaller brain), download it in Step 4, and select it in Step 5.

- **I'm on a work computer and it still won't connect.**
  That's okay — the tool talks to the brain directly on your own machine and never through
  your company's network, so it still works. If it stays off, ask your IT helper to confirm
  Ollama is installed.

---

## The short version (once you've done it once)

1. Open the typing window (Terminal).
2. Type `ollama pull` + the brain name (e.g. `ollama pull qwen2.5:14b`) and press Enter; wait
   for **success**.
3. In the tool: **AI Settings → Model →** pick the new brain → **Save**.
4. Look for the green **"Local AI is ON"**. Done.

Your schedule stays private the entire time — only the brain download uses the internet.

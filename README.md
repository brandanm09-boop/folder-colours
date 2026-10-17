# Folder Colours

Give each VS Code folder its own colours, so you always know which project window you are in. It also sets the font and text size of the Claude Code chat panel.

## Use it

```
git clone <this repo>
python3 folder-colours/colours.py ~/path/to/your/project
```

A page opens in your browser. Click a look. That folder's VS Code window changes as you click. Press Ctrl+C in the terminal when you are done.

Several folders at once:

```
python3 folder-colours/colours.py ~/Work/*OS
```

## On the page

- **Pick a look** sets the border, background, text, lines and highlight in one click.
- **Change one part** lets you set any of those on its own, plus the Claude chat font and size.
- **Undo** steps back. **Remove colours** puts the folder back to your normal theme.

## What it changes

It writes three settings into that folder's `.vscode/settings.json`: `workbench.colorCustomizations`, `chat.fontFamily` and `chat.fontSize`. Every other setting in the file is kept. Comments in that file are not kept, so the first time it edits a file it did not make, it saves the original alongside as `settings.before-folder-colours.json`.

Your picks are stored on the first line of that file, so the page remembers them next time.

## Needs

Python 3, which comes with macOS. Nothing to install. The page only runs on your own machine at `127.0.0.1` and only accepts saves from itself.

`picker.html` also opens on its own as a preview, with a Copy settings button instead of saving.

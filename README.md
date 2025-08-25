# Python Scripts

This repository contains a variety of Python scripts ranging from command-line utilities to graphical games and test preparation tools. Below is a brief overview and usage instructions for each script.

---

## Utilities

### `powerball.py`  
**Description:** Command-line interface for powerball.com lottery information.  
```bash
python3 powerball.py [-List|-L]
```

### `dnet-user-stats.py`  
**Description:** Command-line interface to stats.distributed.net user/project stats.  
```bash
python3 dnet-stats.py -p <project> -u <user>
```

### `ua-pay.py`  
**Description:** Command-line interface for University of Arizona payroll information.  
```bash
python3 ua-pay.py -fn <first_name> -ln <last_name>
```

### `iso2usb-mac.py`  
**Description:** Easily write ISO images to USB sticks on macOS.  
```bash
python3 iso2usb-mac.py
```

### `text2watermark.py`  
**Description:** Convert text to a PNG watermark image.  
```bash
python3 text2watermark.py <text>
```

### `chatgpt.py`  
**Description:** Command-line interface to chat.openai.com.  
```bash
python3 chatgpt.py
```

### `diff-web.py`  
**Description:** Monitor a website and send diffs to stdout, a log file, email, or webhook.  
```bash
python3 diff-web.py --domain example.com --email user@example.com --hook example.com/hook
```

### `topless.py`  
**Description:** Display top system processes with color.  
```bash
python3 topless.py
```

---

## Amateur Radio Test Preparation

### `ham-test-cli.py`  
**Description:** Amateur Radio Operator License test preparation tool (Command Line Interface).  
```bash
python3 ham-test-cli.py
```

### `ham-test-gui.py`  
**Description:** Amateur Radio Operator License test preparation tool (Graphical User Interface).
```bash
python3 ham-test-gui.py
```

### `ham-test-www.py`  
**Description:** Amateur Radio Operator License test preparation tool (Web Browser).
```bash
python3 ham-test-www.py
```

---

## Screensavers

### `matrix-screensaver.py`  
**Description:** The Matrix-themed screensaver.  
```bash
python3 matrix-screensaver.py
```

### `sushi-screensaver.py`  
**Description:** Sushi-themed screensaver.  
```bash
python3 sushi-screensaver.py
```

---

## Games

### `circlewars-game.py`  
**Description:** Red vs Blue circles game.  
```bash
python3 circlewars-game.py
```

**Controls:**  
- Movement: `W`, `A`, `S`, `D` (Keyboard) or Direction-pad (Controller)  
- Fire: `Spacebar` (Keyboard), Primary-click (Mouse), or `A` button (Controller)  
- Pause/Exit: `Esc` (Keyboard) or `Start` (Controller), then `Q` (Keyboard) or `X` (Controller)

### `maguro-game.py`  
**Description:** Maguro Cat eats sushi game.  
```bash
python3 maguro-game.py
```

**Controls:**  
- Movement: `A` (Left), `D` (Right) (Keyboard) or Joy-pad (Controller)  
- Pause/Exit: `Esc` (Keyboard) or `Start` (Controller), then `Q` (Keyboard) or `X` (Controller)

### `tankwars-game.py`  
**Description:** Red vs Blue tanks game.  
```bash
python3 tankwars-game.py
```

**Controls:**  
- Movement: `W`, `A`, `S`, `D` (Keyboard) or Direction-pad (Controller)  
- Fire: `Spacebar` (Keyboard), Primary-click (Mouse), or `A` button (Controller)  
- Pause/Exit: `Esc` (Keyboard) or `Start` (Controller), then `Q` (Keyboard) or `X` (Controller)

---

_Designed and tested on Mac and Linux. May or may not work on Windows. \*shrug\*_

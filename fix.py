import os

path = "tests/test_gui_app.py"
with open(path, "r") as f:
    c = f.read()

c = c.replace('assert gui_app._run_button.cget("state") == "normal"', 'assert str(gui_app._run_button.cget("state")) == "normal"')
c = c.replace('assert gui_app._cancel_button.cget("state") == "disabled"', 'assert str(gui_app._cancel_button.cget("state")) == "disabled"')

with open(path, "w") as f:
    f.write(c)

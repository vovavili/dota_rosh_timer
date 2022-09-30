=========================
DotA 2 Roshan Death Timer
=========================

.. image:: rosh_death_timer_preview.png
    :align: center


DotA 2 Roshan death timer macros, using computer vision. Tracks expiration time, minimum and
maximum respawn timer as contents of your clipboard. Handy in combination with `Win+V <https://support.microsoft.com/en-us/windows/clipboard-in-windows-c436501e-985d-1c8d-97ea-fe46ddf338c6>`_ clipboard hotkey.
Should work on any 1920x1080 screen.

You may or may not get VAC-banned for using this in your games, though I *presume* that a ban is unlikely as you are not interacting with DotA files in any direct or indirect way.
Use on your own risk.

By default, this tracks the Rosh timer. One can also specify command line arguments to track metrics like glyph and buyback cooldowns.


Installation guide
--------

#. Install Python_. Make sure not to untick the box to register Python directory in your PATH variable.
#. Open a Windows Terminal from the Start menu and copy-paste the following command: ``pip install setuptools --user``
#. Download and extract this repository using *Code -> Download ZIP* button at the top of this page, slightly to the right.
#. Install required dependencies by double-clicking on the *setup.py* file.
#. Set up a macros to run *"rosh_death_timer.pyw"* script using a hotkey of your choice. I either recommend using your specialized mouse and keyboard software or AutoHotKey_.
#. Additionally, specify other macros to run the same script with ``glyph`` or ``buyback`` arguments.
#. The first run will take significantly longer.

Contributing
-------
Pull requests are always welcome.

TODO
-------
* Make this work on screens other than 1920x1080
* The script runtime takes a couple of seconds. I wonder if that could be improved?
* Adding a couple of other timers for abilities using OpenDotA's DotA constants API would be neat.

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template. All the heavy
lifting is done with EasyOCR_.

.. _AutoHotKey: https://www.autohotkey.com/docs/commands/Run.htm
.. _Python: https://www.python.org/downloads/
.. _EasyOCR: https://github.com/JaidedAI/EasyOCR
.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage

License
-------
MIT

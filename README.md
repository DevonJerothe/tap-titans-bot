![TapTitansBot Logo](media/flame.png)

[![Release](https://img.shields.io/github/v/release/becurrie/tap-titans-bot?color=blue&label=Release&logo=github&logoColor=white)](https://github.com/becurrie/tap-titans-bot/releases/latest)
[![Discord](https://img.shields.io/discord/858396057497894943?color=blue&label=Discord&logo=discord&logoColor=white)](https://discord.com/eUyUxwSAVy)
[![Paypal](https://img.shields.io/badge/Paypal.me-blue.svg?label=Donate&logo=paypal&logoColor=white)](https://paypal.me/becurrie)

# Tap Titans Bot

## I Just Want To Use The Bot?

If you're here and you just want to download and run the application, look in the
[releases](https://github.com/becurrie/tap-titans-bot/releases) section of this repository for the .exe file that can be ran without setting
up a development environment. Note that your system will need to meet the requirements
below for the bot to work properly.

### Application Requirements

* Windows 10 (64 Bit)
* Windows Resolution Greater Than 480x800
* Supported Android Emulator (Nox/MEmu)
* Supported Android Emulator Resolution: 480x800

### How Do I Use The Bot?

A small tutorial is available [here](https://github.com/becurrie/tap-titans-bot/wiki/Using-The-Application) with instructions on running and using the
application, if you're running into issues, you can also join the [discord](https://discord.com/eUyUxwSAVy) server
for additional help.

---

The following instructions are meant to help someone get the repository pulled
down and in a state where they can develop and run the application with Python instead
of using the bundled .exe file included in a release.

## Development Requirements

* [Python 3.7](https://www.python.org/downloads/release/python-370/)
  * Ensure you install the correct version of Python as some of the requirements
    may not work with a different versions.

* Virtual environment (or main python env) with project dependencies installed (requirements.txt)
  * `pip install -r requirements.txt`

## Installation

* Clone this repository (using Git, or downloading the source code)
* Follow development requirements above
* Run `application.py` to boot up the program

## Contributing

Pull requests are welcome, for any major changes, please open an issue first to discuss
the feature/change that you would like to see. Please take a look at the [wiki](https://github.com/becurrie/tap-titans-bot/wiki) as well for
more information and documentation about contributing to this project.

### Plugins

Most features/enhancements will come in the form of plugins. For more information about developing/modifying plugins,
please look [here](https://github.com/becurrie/tap-titans-bot/wiki/Plugins).

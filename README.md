# Twitter Phishing Bot
Leon Kempers

## Description
This is the source code of the bot I created for my thesis. Please feel free to use and/or modify it for your own research. Crediting my thesis `Kempers, L. (2016). Phishing Through Social Bots: The Organizational Threat and Mitigation Strategies. University of Amsterdam.` would be appreciated.

## Requirements
To set-up a social bot, you need:
* A MySQL database
* Twitter API credentials
* Flickr API credentials
* Bit.ly API credentials
* Alchemy API credentials
* A web server with FTP support (optional, only needed for `dms.py`)

## Installation
1. Edit `config.ini` with your own credentials.
2. Run `python db.py init`.
3. Run `python related.py` to set-up the related keywords and accounts.
4. Run `python probs.py` to initialize the probabilities.

## Tweaking
Repeat step 3 and 4 above to change the related keywords/accounts and probabilities while the bot is running.

## Running the bot
Simply let `bot.py` run as long as you want the bot to be active. Please note that the bot "sleeps" between 10 PM and 8 PM.

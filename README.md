# This is a Zulip Bot

## What it does
It will help you link files from a webdav host (NextCloud) without leaving Zulip

## Usage
@Nextcloud recent [date]

It will
* delete your calling message (if allowed to)
* send you a DM with list of recent files
* wait for you to select files you want to link
* send a message in the original topic with the links you selected

## Install
* Create a Zulip Generic bot
* Deploy a Docker for the bot (see DockerFile)
* Set env variables (see .env.example)
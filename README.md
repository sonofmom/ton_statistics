# ton_statistics
This repository contains tools to collect statistics from Telegram Open Network

For now it collects the mining statistics only

## Usage
Please review example_config.json file and make adjustments to your liking. I advise to leave the intervals as they are/

### collector.py
Creates databases and fills them with data. This is a foreground process that is intended to be run under process monitoring tool such as Daemontools

### graph.py
Generates graphs, this process will exit after completion and should be started from Crontab if regular updates are needed


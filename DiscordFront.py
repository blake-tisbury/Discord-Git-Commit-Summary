import datetime
import os
import asyncio
import discord
from discord.ext import commands, tasks
from discord_components import *
from dotenv import load_dotenv
from GitRunner import GitRunner


class GitDiscordBot(commands.Bot):
    def __init__(
            self, git_url: str,
            git_token: str, channel: int,
            discord_token: str, command_prefix: str,
            scheduled_hour: int, scheduled_minute: int, **options
    ):
        super().__init__(command_prefix, **options)

        self.channel = channel
        self.discord_token = discord_token
        self.scheduled_hour = scheduled_hour
        self.scheduled_minute = scheduled_minute
        self.git_runner = GitRunner(git_url, git_token)
        self.run(self.discord_token)

        self.commits_body = None
        self.list_memo = None

    async def on_ready(self):
        DiscordComponents(self)
        print("Bot running with:")
        print("Username: ", self.user.name)
        print("User ID: ", self.user.id)
        print("[INFO] Bot is ready.")

        self.update_discord_scheduler.start()

    @tasks.loop(hours=24)
    async def update_discord_scheduler(self):
        # calculate how seconds until it's time to update
        now = datetime.datetime.now()
        est = datetime.datetime.now() - datetime.timedelta(hours=5)  # EST
        est = est.replace(hour=self.scheduled_hour, minute=0, second=0, microsecond=0)
        if est < now:
            est = est + datetime.timedelta(days=1)
        time_until_update = (est - now).total_seconds()

        if time_until_update < 0:
            time_until_update += 86400  # if it's already past our time, add a day

        # formate time until update to a readable format
        formatted_time = str(datetime.timedelta(seconds=time_until_update))
        formatted_time = formatted_time.split('.')[0]
        formatted_time = formatted_time.split(':')

        # remove zero in front of numbers if it's less than 10
        for i in range(len(formatted_time)):
            if formatted_time[i][0] == '0':
                formatted_time[i] = formatted_time[i][1:]

        formatted_time = formatted_time[0] + ' hours and ' + formatted_time[1] + f' minute{"" if formatted_time[1] == "1" else "s"}'

        print(f'[INFO] Scheduled update to #{self.get_channel(self.channel).name} in {formatted_time}.')

        await asyncio.sleep(time_until_update)
        await self.git_update()

    async def git_update(self):
        print("[INFO] Getting Git commits...")
        self.commits_body = ""
        self.list_memo = {}

        for branch in await self.git_runner.get_branches():
            await self.format_commits(branch)

        number_of_commits = len(self.list_memo)

        if number_of_commits == 0:
            self.commits_body = "No new commits today, devs are lazy :("

        channel = self.get_channel(self.channel)
        em = discord.Embed(title=f"**Number of commits today: {str(number_of_commits)}**",
                           description=self.commits_body,
                           color=0xceceff)
        print("[INFO] Sending Git commits to Discord...")
        msg = await channel.send(
            embed=em)
        print(
            f"[INFO] #{channel.name} updated with {str(number_of_commits)} new commit{'' if str(number_of_commits) == 1 else 's'}.")

    async def format_commits(self, branch):

        commits = await self.git_runner.get_commits(branch, 1)

        for commit in commits:
            # checks for duplicate commits
            if commit['commit']['message'] in self.list_memo.keys():
                break
            self.list_memo[(commit['commit']['message'])] = None

            if commit['commit']['message'] == commit['commit']['message'].split('\n')[-1]:
                description = ""
            else:
                description = '\n*' + commit['commit']['message'].split('\n')[-1] + '*'

            self.commits_body += (
                                         "**" + commit['commit']['author']['name'].split(' ')[
                                     0]  # gets first name of author
                                         + ' committed: **'
                                         + "`" + commit['commit']['message'].split('\n')[0] + "`"  # commit message
                                         + description) + '\n \n'


if __name__ == "__main__":
    # testing
    path = 'tokens.env'
    load_dotenv(dotenv_path=path, verbose=True)
    bot = GitDiscordBot(
        'https://github.com/blake-tisbury/sumo-man-game.git', os.getenv('GITHUB_TOKEN'),
        921133589364633672, os.getenv('DISCORD_TOKEN'), "$sumo_git", 17, 45)  # runs at 5:45 PM

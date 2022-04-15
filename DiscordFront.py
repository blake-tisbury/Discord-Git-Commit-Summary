import os
import asyncio
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord_components import *
from GitRunner import GitRunner


class GitDiscordBot(commands.Bot):
    def __init__(self, git_url: str, git_token: str, channel: int, discord_token: str, command_prefix: str, **options):
        super().__init__(command_prefix, **options)

        self.channel = channel
        self.discord_token = discord_token
        self.git_runner = GitRunner(git_url, git_token)
        self.run(self.discord_token)

        self.commits_body = None
        self.list_memo = None

    async def on_ready(self):
        DiscordComponents(self)
        print("Bot running with:")
        print("Username: ", self.user.name)
        print("User ID: ", self.user.id)

        loop = asyncio.get_event_loop()
        loop.create_task(self.update_scheduler(60 * 60 * 24))

    async def update_scheduler(self, timeout):
        while True:
            await self.git_update()
            print("[INFO] Updated Discord.")
            await asyncio.sleep(timeout)

    async def git_update(self):
        self.commits_body = ""
        self.list_memo = {}

        for branch in await self.git_runner.get_branches():
            await self.format_commits(branch)

        if (len(self.list_memo)) == 0:
            self.commits_body = "No new commits today, devs are lazy :("

        channel = self.get_channel(self.channel)
        em = discord.Embed(title=f"**Number of commits today: {str(len(self.list_memo))}**",
                           description=self.commits_body,
                           color=0xceceff)
        msg = await channel.send(
            embed=em)

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
        849180725047590922, os.getenv('DISCORD_TOKEN'), "!")

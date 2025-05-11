from core import Cog
from discord.ext import tasks
import datetime
import os
import shutil

class CleanTemp(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cleaner.start()

    def cog_unload(self):
        self.cleaner.cancel()
    
    @tasks.loop(seconds=(300))
    async def cleaner(self):
        remove_after = 150
        now = datetime.datetime.now()
        print("Cleaning temp files")
        for dir in os.listdir("/tmp/"): # this is not great, but Gradio keeps making extra directories without an explanation!!
            dir_time = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join("/tmp/", dir)))
            # find all empty directories that are 40 chars long
            if len(dir) == 40 and os.path.isdir(os.path.join("/tmp/", dir)) and (now - dir_time).seconds > remove_after:
                shutil.rmtree(os.path.join("/tmp/", dir))

        for file in os.listdir("/tmp/"):
            if file.startswith("utilitybelt_"):
                file_path = os.path.join("/tmp/", file)
                file_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                if (now - file_time).seconds > remove_after:
                    if os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                    else:
                        os.remove(file_path)

        for file in os.listdir("temp/"):
            file_path = os.path.join("temp/", file)
            file_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
            if (now - file_time).seconds > remove_after:
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
    @cleaner.before_loop
    async def before_cleaner(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(CleanTemp(bot))
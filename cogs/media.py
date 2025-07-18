import discord
import os
import asyncio
from functools import partial
from core import Cog, Context, utils
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageSequence
from tempfile import NamedTemporaryFile
import aiohttp
import datetime
import yt_dlp

async def image_to_gif(image, url):
    """Convert an image from a URL to a gif and return it as a file path"""
    image = await utils.image_or_url(image, url)
    with NamedTemporaryFile(prefix="utilitybelt_", suffix=".gif", delete=False) as temp_gif:
        image.save(temp_gif, format="PNG", save_all=True, append_images=[image])
        temp_gif.seek(0)
        return discord.File(fp=temp_gif.name)
    
async def get_user_avatar(user: discord.User):
    """Get a user's avatar"""
    user_avatar = user.avatar
    # resize to 256x256
    user_avatar = user_avatar.with_size(256)
    return user_avatar


async def speech_bubble(image, url, overlay_y):
    """Add a speech bubble to an image"""
    overlay = "assets/speechbubble.png"
    overlay = Image.open(overlay).convert("RGBA")

    image = await utils.image_or_url(image, url)
    image = image.convert("RGBA")

    overlay = overlay.resize((image.width, int(image.height * (overlay_y / 10))))

    output = Image.new("RGBA", image.size)
    output.paste(overlay, (0, 0), overlay)

    frame = ImageChops.composite(output, image, output)
    frame = ImageChops.subtract(image, output)
    
    with NamedTemporaryFile(prefix="utilitybelt_",  suffix=".gif", delete=False) as temp_image:
        frame.save(temp_image, format="PNG")
        temp_image.seek(0)
        return discord.File(fp=temp_image.name)


async def download_media_ytdlp(url, download_mode, video_quality, audio_format):

    ytdl_options = {
        "format": "best",
        "outtmpl": "temp/%(uploader)s - %(title).150B.%(ext)s", # limit title to 150 bytes
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "noprogress": True,
        "nocheckcertificate": True,
        "cookiefile": ".cookies",
        "color": "never",
    }

    # default options
    if video_quality == "auto":
        video_quality = "480"
    if audio_format == "auto":
        audio_format = "mp3"

    if download_mode == "audio":
        ytdl_options["format"] = f"""
        bestaudio[ext={audio_format}]/
        bestaudio[acodec=aac]/
        bestaudio/
        best
        """

    if download_mode == "auto":
        ytdl_options["format"] = f"""
        bestvideo[vcodec=h264][height<={video_quality}]+bestaudio[acodec=aac]/
        bestvideo[vcodec=h264][height<={video_quality}]+bestaudio/
        bestvideo[vcodec=vp9][ext=webm][height<={video_quality}]+bestaudio[ext=webm]/
        bestvideo[vcodec=vp9][ext=webm][height<={video_quality}]+bestaudio/
        bestvideo[height<={video_quality}]+bestaudio/
        bestvideo+bestaudio/
        best
        """

    ytdl = yt_dlp.YoutubeDL(ytdl_options)

    # Run blocking operations in thread pool
    loop = asyncio.get_event_loop()
    try:
        info = await loop.run_in_executor(
            None,
            partial(ytdl.extract_info, url, download=True),
        )

        # print available codecs
        # for format in info["formats"]:
        #     format_id = format.get("format_id", "N/A")
        #     ext = format.get("ext", "N/A") 
        #     height = format.get("height", "N/A")
        #     vcodec = format.get("vcodec", "N/A")
        #     acodec = format.get("acodec", "N/A")
        #     format_note = format.get("format_note", "N/A")
        #     print(format_id, ext, height, vcodec, format_note, acodec)

    except yt_dlp.DownloadError as e:
        raise discord.errors.ApplicationCommandError(f"Error: {e}")
    except yt_dlp.ExtractorError as e:
        raise discord.errors.ApplicationCommandError(f"Error: {e}")


    filepath = ytdl.prepare_filename(info)

    print (filepath)

    return discord.File(fp=filepath)
  
async def upload_to_catbox(file): # pass a discord.File object
    """Upload media to catbox.moe with curl and return the URL"""
    file_raw = open(file.fp.name, "rb")
    file_type = file.filename.split(".")[-1]
    data = aiohttp.FormData()
    data.add_field("reqtype", "fileupload")
    data.add_field("time", "72h")
    data.add_field("fileToUpload", file_raw, filename="file.{}".format(file_type))
    async with aiohttp.ClientSession() as session:
        async def post(data) -> str:
            async with session.post("https://litterbox.catbox.moe/resources/internals/api.php", data=data) as response:
                text = await response.text()
                if not response.ok:
                    return None
                return text
        return await post(data)

async def upload_to_imgur(file): # pass a discord.File object
    """Upload media to Imgur anonymously and return the album URL"""
    async with aiohttp.ClientSession() as session:
        try:
            # Read the file
            with open(file.fp.name, 'rb') as f:
                file_data = f.read()
            
            # Prepare the form data
            data = aiohttp.FormData()
            data.add_field('image', file_data, filename=file.filename)
            
            # Upload to Imgur's anonymous upload endpoint
            async with session.post('https://api.imgur.com/3/image', data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    direct_link = result['data']['link']
                    image_id = direct_link.split('/')[-1].split('.')[0]
                    imgur_link = f"https://imgur.com/{image_id}"
                    return imgur_link
                else:
                    error_text = await response.text()
                    raise discord.errors.ApplicationCommandError(f"Failed to convert to gif: {error_text}")
        except Exception as e:
            raise discord.errors.ApplicationCommandError(f"Failed to convert to gif: {str(e)}")

async def add_caption(image, url, caption_text):
    """Add a caption above an image or gif, extending the canvas with a white background, wrapping text into multiple lines if needed."""
    font_path = "assets/Futura Extra Bold Condensed.otf"
    image = await utils.image_or_url(image, url)
    is_animated = getattr(image, "is_animated", False)
    frames = []
    duration = image.info.get("duration", 100)
    def process_frame(frame):
        frame = frame.convert("RGBA")
        width, height = frame.size
        # Fixed bar height and font size (13% of image height)
        bar_height = int(height * 0.13)
        font_size = int(bar_height * 0.7)
        font = ImageFont.truetype(font_path, font_size)
        # Wrap text so each line fits the image width
        words = caption_text.split()
        lines = []
        current_line = ""
        draw = ImageDraw.Draw(frame)
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            bbox = draw.textbbox((0,0), test_line, font=font)
            if bbox[2] - bbox[0] <= width - 20:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        total_bar_height = bar_height * len(lines)
        new_img = Image.new("RGBA", (width, height + total_bar_height), (255,255,255,255))
        # Paste original image below the bars
        new_img.paste(frame, (0, total_bar_height), frame)
        draw = ImageDraw.Draw(new_img)
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0,0), line, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (width - text_width) // 2
            y = int(i * bar_height + (bar_height - text_height) // 2)
            draw.text((x, y), line, font=font, fill="black")
        return new_img.convert("RGB")
    if is_animated:
        for frame in ImageSequence.Iterator(image):
            frames.append(process_frame(frame))
        frames_p = [f.convert("P", dither=Image.NONE, palette=Image.ADAPTIVE) for f in frames]
        with NamedTemporaryFile(prefix="utilitybelt_", suffix=".gif", delete=False) as temp_gif:
            frames_p[0].save(temp_gif, save_all=True, append_images=frames_p[1:], format="GIF", duration=duration, loop=0, disposal=2)
            temp_gif.seek(0)
            return discord.File(fp=temp_gif.name)
    else:
        new_img = process_frame(image)
        with NamedTemporaryFile(prefix="utilitybelt_", suffix=".png", delete=False) as temp_img:
            new_img.save(temp_img, format="PNG")
            temp_img.seek(0)
            return discord.File(fp=temp_img.name)

class Media(Cog):
    """Media Commands"""

    @discord.slash_command(
        integration_types={
        discord.IntegrationType.guild_install,
        discord.IntegrationType.user_install,
        },
        name="image-to-gif",
        description="Convert an image to a gif"
    )
    @discord.option(
        "url",
        description="The URL of the image to convert",
        type=str,
        required=False
    )
    @discord.option(
        "image",
        description="The image to convert",
        type=discord.Attachment,
        required=False
    )
    async def image_to_gif_command(self, ctx: Context, image: discord.Attachment = None, url: str = None):
        """Convert an image to a gif using image_to_gif"""
        await ctx.respond(content = f"Converting image to gif {self.bot.get_emojis('loading_emoji')}")
        if not image and not url:
            raise discord.errors.ApplicationCommandError("No image or URL provided")
        
        # If url is a message ID, try to get the message and its attachments
        if url and url.isdigit():
            try:
                message = await ctx.channel.fetch_message(int(url))
                if message.attachments:
                    image = message.attachments[0]
                    url = None
                else:
                    raise discord.errors.ApplicationCommandError("No image found in the referenced message")
            except discord.NotFound:
                raise discord.errors.ApplicationCommandError("Message not found")
            except discord.Forbidden:
                raise discord.errors.ApplicationCommandError("Cannot access the referenced message")
        
        file = await image_to_gif(image, url)
        await ctx.edit(content = f"", file=file)
        os.remove(file.fp.name)

    @discord.message_command(
        integration_types={
            discord.IntegrationType.guild_install,
            discord.IntegrationType.user_install,
        },
        name="image-to-gif",
        description="Convert an image to a gif"
    )
    async def image_to_gif_message_command(self, ctx: Context, message: discord.Message):
        """Convert an image to a gif using image_to_gif"""
        await ctx.respond(content = f"Converting image to gif {self.bot.get_emojis('loading_emoji')}")
        if not message.attachments:
            raise discord.errors.ApplicationCommandError("No image attached to message")
        file = await image_to_gif(message.attachments[0], message.attachments[0].url)
        await ctx.edit(content = f"", file=file)
        os.remove(file.fp.name)

    @discord.slash_command(
        integration_types={
        discord.IntegrationType.guild_install,
        discord.IntegrationType.user_install,
        },
        name="speech-bubble",
        description="Add a speech bubble to an image"
    )

    @discord.option(
    "url",
    description="The URL of the image to add a speech bubble to",
    type=str,
    required=False
    )
    @discord.option(
        "image",
        description="The image to add a speech bubble to",
        type=discord.Attachment,
        required=False
    )
    @discord.option(
        "overlay_y",
        description="The height of the speech bubble overlay",
        type=int,
        required=False,
        default=2
    )
    async def speech_bubble_command(self, ctx: Context, image: discord.Attachment = None, url: str = None, user: discord.User = None, overlay_y: int = 2):
        """Add a speech bubble to an image using speech_bubble"""
        await ctx.respond(content = f"Adding speech bubble to image {self.bot.get_emojis('loading_emoji')}")
        if not image and not url and not user:
            raise discord.errors.ApplicationCommandError("No image or URL provided")
        if user != None:
            image = await get_user_avatar(user)
        if overlay_y <= 0 or overlay_y > 10:
            raise discord.errors.ApplicationCommandError("Overlay y must be between 0 and 10")
        file = await speech_bubble(image, url, overlay_y)
        await ctx.edit(content = f"", file=file)
        os.remove(file.fp.name)

    @discord.message_command(
        integration_types={
            discord.IntegrationType.guild_install,
            discord.IntegrationType.user_install,
        },
        name="speech-bubble",
        description="Add a speech bubble to an image"
    )
    async def speech_bubble_message_command(self, ctx: Context, message: discord.Message):
        """Add a speech bubble to an image using speech_bubble"""
        await ctx.respond(content = f"Adding speech bubble to image {self.bot.get_emojis('loading_emoji')}")
        if not message.attachments:
            raise discord.errors.ApplicationCommandError("No image attached to message")
        file = await speech_bubble(message.attachments[0], message.attachments[0].url, 2)
        await ctx.edit(content = f"", file=file)
        os.remove(file.fp.name)


    @discord.slash_command(
        integration_types={
        discord.IntegrationType.guild_install,
        discord.IntegrationType.user_install,
        },
        name="download",
        description="Download media from a URL"
    )
    @discord.option(
        "url",
        description="The URL of the media to download",
        type=str,
        required=True,
    )   
    @discord.option(
        "format",
        description="The type of media to download",
        type=str,
        choices=["auto", "audio"],
        required=False,
        default="auto",
    )
    @discord.option(
        "video_quality",
        description="The download quality",
        type=str,
        choices=["auto", "144", "240", "360", "480", "720", "1080"],
        default="auto",
        required=False,
    )
    @discord.option(
        "audio_format",
        description="The audio format",
        type=str,
        choices=["auto", "mp3", "wav", "opus", "ogg"],
        default="auto",
        required=False,
    )

    async def download_media_command(self, ctx: Context, url: str, format: str, video_quality: str, audio_format: str):
        """Download media from a URL using download_media"""
        await ctx.defer()
        try:
            url_short = url.split('/')[2]
        except IndexError:
            url_short = url
        await ctx.respond(content = f"Downloading media from {url_short} {self.bot.get_emojis('loading_emoji')}")
        file = await download_media_ytdlp(url, format, video_quality, audio_format)
        try:
            await ctx.edit(content = f"", file=file)
        except discord.errors.HTTPException:
            await ctx.edit(content = f"Media is too big for discord, uploading to litterbox.catbox.moe instead {self.bot.get_emojis('loading_emoji')}")
            catbox_link = await upload_to_catbox(file)
            # get timestamp of 3 days from now in unix timestamp
            
            timestamp = datetime.datetime.now() + datetime.timedelta(days=3)
            timestamp = int(timestamp.timestamp())
            timestamp = str(f"<t:{timestamp}:R>")
            if catbox_link is not None:
                await ctx.edit(content = f"Expiry: {timestamp} {catbox_link}")
            else:
                await ctx.edit(content = f"Failed to upload to catbox.moe (file is probably still too big)")
        os.remove(str(file.fp.name))

    @discord.slash_command(
        integration_types={
            discord.IntegrationType.guild_install,
            discord.IntegrationType.user_install,
        },
        name="video-to-gif",
        description="Convert video to a gif"
    )
    @discord.option(
        "url",
        description="The URL of the video/media to upload",
        type=str,
        required=False
    )
    @discord.option(
        "media",
        description="The video/media file to upload",
        type=discord.Attachment,
        required=False
    )
    async def video_to_gif_command(self, ctx: Context, media: discord.Attachment = None, url: str = None):
        """Convert video to a gif"""
        await ctx.respond(content = f"Converting media to gif {self.bot.get_emojis('loading_emoji')}")
        # If url is a message ID, try to get the message and its attachments
        if url and url.isdigit():
            try:
                message = await ctx.channel.fetch_message(int(url))
                if message.attachments:
                    media = message.attachments[0]
                    url = None
                else:
                    raise discord.errors.ApplicationCommandError("No media found in the referenced message")
            except discord.NotFound:
                raise discord.errors.ApplicationCommandError("Message not found")
            except discord.Forbidden:
                raise discord.errors.ApplicationCommandError("Cannot access the referenced message")
        
        # Download the media if it's a URL
        if url:
            file = await download_media_ytdlp(url, "auto", "auto", "auto")
        else:
            # For attachments, we need to download them first
            async with aiohttp.ClientSession() as session:
                async with session.get(media.url) as response:
                    if response.status != 200:
                        raise discord.errors.ApplicationCommandError("Failed to download media")
                    
                    # Create a temporary file
                    with NamedTemporaryFile(prefix="utilitybelt_", suffix=f".{media.filename.split('.')[-1]}", delete=False) as temp_file:
                        temp_file.write(await response.read())
                        temp_file.seek(0)
                        file = discord.File(fp=temp_file.name)
        
        # Upload to Imgur
        imgur_url = await upload_to_imgur(file)
        await ctx.edit(content = f"{imgur_url}")
        os.remove(file.fp.name)

    @discord.message_command(
        integration_types={
            discord.IntegrationType.guild_install,
            discord.IntegrationType.user_install,
        },
        name="video-to-gif",
        description="Upload video/media to Imgur as a GIF"
    )
    async def video_to_gif_message_command(self, ctx: Context, message: discord.Message):
        """Upload video/media to Imgur as a GIF"""
        await ctx.respond(content = f"Converting media to gif {self.bot.get_emojis('loading_emoji')}")
        if not message.attachments:
            raise discord.errors.ApplicationCommandError("No media attached to message")
        
        # Download the attachment
        async with aiohttp.ClientSession() as session:
            async with session.get(message.attachments[0].url) as response:
                if response.status != 200:
                    raise discord.errors.ApplicationCommandError("Failed to download media")
                
                # Create a temporary file
                with NamedTemporaryFile(prefix="utilitybelt_", suffix=f".{message.attachments[0].filename.split('.')[-1]}", delete=False) as temp_file:
                    temp_file.write(await response.read())
                    temp_file.seek(0)
                    file = discord.File(fp=temp_file.name)
        
        # Upload to Imgur
        imgur_url = await upload_to_imgur(file)
        await ctx.edit(content = f"{imgur_url}")
        os.remove(file.fp.name)

    @discord.slash_command(
        integration_types={
            discord.IntegrationType.guild_install,
            discord.IntegrationType.user_install,
        },
        name="caption",
        description="Add a caption above an image or gif (meme style)"
    )
    @discord.option(
        "caption_text",
        description="The caption text to add above the image",
        type=str,
        required=True
    )
    @discord.option(
        "url",
        description="The URL of the image or gif",
        type=str,
        required=False
    )
    @discord.option(
        "image",
        description="The image or gif to caption",
        type=discord.Attachment,
        required=False
    )
    async def caption_command(self, ctx: Context, caption_text: str, image: discord.Attachment = None, url: str = None):
        """Add a meme-style caption above an image or gif"""
        await ctx.respond(content = f"Adding caption... {self.bot.get_emojis('loading_emoji')}")
        file = await add_caption(image, url, caption_text)
        await ctx.edit(content = f"", file=file)
        os.remove(file.fp.name)

def setup(bot):
    bot.add_cog(Media(bot))

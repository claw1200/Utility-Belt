import discord
from discord.utils import utcnow
from core import Cog, Context, utils
from pint import UnitRegistry
import base64
import codecs
from qrcode import QRCode, constants
import hashlib
import os
from PIL import Image
from numpy import array
import time
import datetime
import dateutil.parser
from os import getenv
import aiohttp
from difflib import SequenceMatcher
import pint

def convert_str_to_unix_time(string):
    # Parse the string into a time
    try:
        dt = dateutil.parser.parse(string)
    except dateutil.parser._parser.ParserError:
        return None
    # Convert the time object to a Unix timestamp and return it
    return int(time.mktime(dt.timetuple()))

async def call_api_holidays(country_code, year):
    # Look up string to see if it's a holiday
    # holiday_type = 'public_holiday'
    api_url = "https://api.api-ninjas.com/v1/holidays?country={}&year={}".format(country_code, year)
    # get api key
    api_key = getenv("ninja")
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, headers={'X-Api-Key': api_key}) as response:
            response.raise_for_status()
            return await response.json()

def similar(a, b):
    """Return a similarity score between 0 and 1 for two strings"""
    return SequenceMatcher(None, a, b).ratio()

async def timecode_convert(time_string, format):
    # Examples:
    # <t:1704206040:R>
    # <t:1704206040:t>
    # <t:1704206040:T>
    # <t:1704206040:d>
    # <t:1704206040:D>
    # <t:1704206040:f>
    # <t:1704206040:F>

    # Convert it to Unix time
    if time_string == None:
        unix_time = time.time()
    else:
        unix_time = convert_str_to_unix_time(time_string)
        if unix_time is None:
            possible_holidays = await call_api_holidays("CA", datetime.datetime.now().year)
            possible_holidays.extend(await call_api_holidays("CA", datetime.datetime.now().year + 1))
            
            unique_holidays = {}
            today = datetime.datetime.now()

            for holiday in possible_holidays:
                name = holiday["name"].lower()
                date = datetime.datetime.strptime(holiday['date'], "%Y-%m-%d")  # assuming date is in this format

                if name not in unique_holidays:
                    unique_holidays[name] = date
                else:
                    if date > today:
                        if unique_holidays[name] < today or date < unique_holidays[name]:
                            unique_holidays[name] = date
                    # if date is before today, ignore it

            # replace possible_holidays with the unique ones
            possible_holidays = [{'name': name, 'date': date.strftime("%Y-%m-%d")} for name, date in unique_holidays.items()]
                    
            max_similarity = 0
            for holiday in possible_holidays:
                similarity = similar(holiday["name"].lower(), time_string.lower())
                if similarity > max_similarity:
                    max_similarity = similarity
                    most_similar_name = holiday["name"].lower()
                    date = holiday['date']
                    unix_time = convert_str_to_unix_time(date)
            if unix_time is None:
                return None
    format = format.lower()
    if format == "relative":
        return f"<t:{int(unix_time)}:R>\n`<t:{int(unix_time)}:R>`"
    if format == "short time":
        return f"<t:{int(unix_time)}:t>\n`<t:{int(unix_time)}:t>`"
    if format == "long time":
        return f"<t:{int(unix_time)}:T>\n`<t:{int(unix_time)}:T>`"
    if format == "short date":
        return f"<t:{int(unix_time)}:d>\n`<t:{int(unix_time)}:d>`"
    if format == "long date":
        return f"<t:{int(unix_time)}:D>\n`<t:{int(unix_time)}:D>`"
    if format == "long date with short time":
        return f"<t:{int(unix_time)}:f>\n`<t:{int(unix_time)}:f>`"
    if format == "long date with day of the week":
        return f"<t:{int(unix_time)}:F>\n`<t:{int(unix_time)}:F>`"
    else:
        return None

def caesar_cipher_encode(message, key):
    encoded_message = ""
    key = int(key)  # Convert the key to an integer
    for char in message:
        if char.isalpha():
            if char.isupper():
                encoded_char = chr((ord(char) - ord('A') + key) % 26 + ord('A'))
            else:
                encoded_char = chr((ord(char) - ord('a') + key) % 26 + ord('a'))
        else:
            encoded_char = char
        encoded_message += encoded_char
    return encoded_message

def vigenere_cipher_encode(message, key):
    encoded_message = ""
    key_length = len(key)
    key_index = 0
    for char in message:
        if char.isalpha():
            key_char = key[key_index % key_length]
            key_offset = ord(key_char.upper()) - ord('A')
            if char.isupper():
                encoded_char = chr((ord(char) - ord('A') + key_offset) % 26 + ord('A'))
            else:
                encoded_char = chr((ord(char) - ord('a') + key_offset) % 26 + ord('a'))
            key_index += 1
        else:
            encoded_char = char
        encoded_message += encoded_char
    return encoded_message

def atbash_cipher_encode(message):
    encoded_message = ""
    for char in message:
        if char.isalpha():
            if char.isupper():
                encoded_char = chr(ord('Z') - (ord(char) - ord('A')))
            else:
                encoded_char = chr(ord('z') - (ord(char) - ord('a')))
        else:
            encoded_char = char
        encoded_message += encoded_char
    return encoded_message

def caesar_cipher_decode(message, key):
    decoded_message = ""
    key = int(key)  # Convert the key to an integer
    for char in message:
        if char.isalpha():
            if char.isupper():
                decoded_char = chr((ord(char) - ord('A') - key) % 26 + ord('A'))
            else:
                decoded_char = chr((ord(char) - ord('a') - key) % 26 + ord('a'))
        else:
            decoded_char = char
        decoded_message += decoded_char
    return decoded_message

def vigenere_cipher_decode(message, key):
    decoded_message = ""
    key_length = len(key)
    key_index = 0
    for char in message:
        if char.isalpha():
            key_char = key[key_index % key_length]
            key_offset = ord(key_char.upper()) - ord('A')
            if char.isupper():
                decoded_char = chr((ord(char) - ord('A') - key_offset) % 26 + ord('A'))
            else:
                decoded_char = chr((ord(char) - ord('a') - key_offset) % 26 + ord('a'))
            key_index += 1
        else:
            decoded_char = char
        decoded_message += decoded_char
    return decoded_message

def atbash_cipher_decode(message):
    decoded_message = ""
    for char in message:
        if char.isalpha():
            if char.isupper():
                decoded_char = chr(ord('Z') - (ord(char) - ord('A')))
            else:
                decoded_char = chr(ord('z') - (ord(char) - ord('a')))
        else:
            decoded_char = char
        decoded_message += decoded_char
    return decoded_message

def binary_to_text(message):
    # Remove spaces and convert binary string to bytes
    binary_string = ''.join(message.split())
    try:
        byte_data = int(binary_string, 2).to_bytes((len(binary_string) + 7) // 8, 'big')
        return byte_data.decode()
    except ValueError:
        return None

def hex_to_text(message):
    # Remove spaces and convert hex string to bytes
    hex_string = ''.join(message.split())
    try:
        byte_data = bytes.fromhex(hex_string)
        return byte_data.decode()
    except ValueError:
        return None
    
def unit_conversion(value: float, unit_from: str, unit_to: str):

    # Parse the units
    ureg = UnitRegistry()
    try:
        unit_from = ureg(unit_from)
        unit_to = ureg(unit_to)
    except pint.errors.UndefinedUnitError:
        raise discord.errors.ApplicationCommandError("Invalid unit")

    # Perform the conversion
    try:
        converted_value = (value * unit_from.to(unit_to)).magnitude
    except pint.errors.DimensionalityError:
        raise discord.errors.ApplicationCommandError("Cannot convert between these units - they are not compatible")
    except AttributeError:
        raise discord.errors.ApplicationCommandError("Invalid unit")
    unit_from = str(unit_from).split(" ")[1]
    unit_to = str(unit_to).split(" ")[1]

    unit_from = f"{unit_from}{utils.s(int(value))}"
    unit_to = f"{unit_to}{utils.s(int(converted_value))}"

    return converted_value, unit_from, unit_to

def qr_code_image_generator(text):
    qr = QRCode(
        version=1,
        error_correction=constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)
    image_seed = hashlib.md5(text.encode()).hexdigest()
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(f"temp/qr{image_seed}.png")
    return f"temp/qr{image_seed}.png"

def qr_code_text_generator(input=None, invert=False, white='█', black=' ', version=1, border=1, correction='M'):
    """Converts a QR code to ASCII art."""
    # generate/load image
    if input is None or not os.path.isfile(input):
        if input:
            data = input
        else:
            data = input('Enter data to encode: ')

        # parse error correction
        if correction == 'L':
            ecc = constants.ERROR_CORRECT_L
        elif correction == 'Q':
            ecc = constants.ERROR_CORRECT_Q
        elif correction == 'H':
            ecc = constants.ERROR_CORRECT_H
        else: # default M
            ecc = constants.ERROR_CORRECT_M

        qr = QRCode(version=version, box_size=1, border=border, error_correction=ecc)
        qr.add_data(data)
        qr.make(fit=True)
        image = qr.make_image(fill_color=(0, 0, 0), back_color=(255, 255, 255))
    else:
        try:
            image = Image.open(input)
        except:
            raise ValueError("unable to open file")

    image_array = array(image.getdata())

    width = image.size[0]
    height = image.size[1]

    # get offset
    offset = 0
    while image_array[offset * width + offset][0] == 255:
        offset += 1

    # get scale
    scale = 1
    while image_array[(offset + scale) * width + (offset + scale)][0] == 0:
        scale += 1

    # resize
    image = image.resize((width // scale, height // scale), Image.Resampling.NEAREST)
    image_array = array(image.getdata())
    width = image.size[0]
    height = image.size[1]

    # inverted colors
    if invert:
        image_array = 255 - image_array

    qr_string = ''
    for i in range(0, height, 2):
        for j in range(width):
            if i + 1 < height:
                upper_pixel = image_array[i * width + j][0] < 128
                lower_pixel = image_array[(i + 1) * width + j][0] < 128
                if upper_pixel and lower_pixel:
                    qr_string += white
                elif upper_pixel:
                    qr_string += '▀'
                elif lower_pixel:
                    qr_string += '▄'
                else:
                    qr_string += black
            else:
                if image_array[i * width + j][0] < 128:
                    qr_string += '▀'
                else:
                    qr_string += black
        qr_string += '\n'
    # remove first space from each line
    if qr_string.startswith(' '):
        qr_string = qr_string[1:]
        qr_string = '\n' + qr_string
    qr_string = qr_string.replace(' \n', '\n')
    qr_string = qr_string.replace('\n ', '\n')
    return qr_string


class Utilities(Cog):
    """Miscellaneous commands"""

    @discord.slash_command(
        integration_types={
        discord.IntegrationType.guild_install,
        discord.IntegrationType.user_install,
        },
        name="decode",
        description="Decode a message using a cipher",
    )
    @discord.option(
        "message",
        description="The message to decode",
        type=str,
        required=True
    )
    @discord.option(
        name="mode",
        description="The cipher to use",
        type=str,
        required=True,
        choices=["base64", "rot13", "caesar", "vigenere", "atbash", "binary", "hex"]
    )
    @discord.option(
        name="key",
        description="The key to use for the cipher",
        type=str,
        required=False
    )
    async def decode_command(self, ctx: Context, message: str, mode: str, key: str = None):
        """Decode a message using a cipher"""
        await ctx.defer()
        await ctx.respond(content = f"Decoding message using {mode} cipher {self.bot.get_emojis('loading_emoji')}")
        decoded_message = None
        if mode == "base64":
            try:
                decoded_bytes = base64.b64decode(message.encode())
                decoded_message = decoded_bytes.decode()
            except ValueError:
                raise discord.errors.ApplicationCommandError("Invalid base64 string")
        if mode == "rot13":
            decoded_message = codecs.decode(message, 'rot_13')
        if mode == "caesar":
            if key is None or not key.isdigit():
                raise discord.errors.ApplicationCommandError("Please enter a valid key for the Caesar cipher")
            decoded_message = caesar_cipher_decode(message, key)
        if mode == "vigenere":
            if key is None:
                raise discord.errors.ApplicationCommandError("Please enter a key for the Vigenere cipher")
            decoded_message = vigenere_cipher_decode(message, key)
        if mode == "atbash":
            decoded_message = atbash_cipher_decode(message)
        if mode == "binary":
            decoded_message = binary_to_text(message)
        if mode == "hex":
            decoded_message = hex_to_text(message)

        return await ctx.edit(content = f"Decoded message: {decoded_message}")
    
    @discord.slash_command(
        integration_types={
        discord.IntegrationType.guild_install,
        discord.IntegrationType.user_install,
        },
        name="encode",
        description="Encode a message using a cipher",
    )
    @discord.option(
        "message",
        description="The message to encode",
        type=str,
        required=True
    )
    @discord.option(
        name="mode",
        description="The cipher to use",
        type=str,
        required=True,
        choices=["base64", "rot13", "caesar", "vigenere", "atbash", "binary", "hex"]
    )
    @discord.option(
        name="key",
        description="The key to use for the cipher",
        type=str,
        required=False
    )
    async def encode_command(self, ctx: Context, message: str, mode: str, key: str = None):
        """Encode a message using a cipher"""
        await ctx.defer()
        await ctx.respond(content = f"Encoding message using {mode} cipher {self.bot.get_emojis('loading_emoji')}")
        encoded_message = None
        if mode == "base64":
            encoded_bytes = base64.b64encode(message.encode())
            encoded_message = encoded_bytes.decode()
        if mode == "rot13":
            encoded_message = codecs.encode(message, 'rot_13')
        if mode == "caesar":
            if key is None or not key.isdigit():
                raise discord.errors.ApplicationCommandError("Please enter a valid key for the Caesar cipher")
            encoded_message = caesar_cipher_encode(message, key)
        if mode == "vigenere":
            if key is None:
                raise discord.errors.ApplicationCommandError("Please enter a key for the Vigenere cipher")
            encoded_message = vigenere_cipher_encode(message, key)
        if mode == "atbash":
            encoded_message = atbash_cipher_encode(message)
        if mode == "binary":
            encoded_message = ' '.join(format(ord(char), '08b') for char in message)
        if mode == "hex":
            encoded_message = ' '.join(format(ord(char), '02x') for char in message)

        return await ctx.edit(content = f"Encoded message: {encoded_message}")


    @discord.slash_command(
        integration_types={
        discord.IntegrationType.guild_install,
        discord.IntegrationType.user_install,
        },
        name="units",
        description="Convert one unit to another"
    )
    @discord.option(
        "value",
        description="The value to convert",
        type=float,
        required=True
    )
    @discord.option(
        "unit_from",
        description="The unit to convert from",
        type=str,
        required=True
    )
    @discord.option(
        "unit_to",
        description="The unit to convert to",
        type=str,
        required=True
    )

    async def units_command(self, ctx: Context, value: float, unit_from: str, unit_to: str):
        """Convert one unit to another"""
        await ctx.defer()
        await ctx.respond(content = f"Converting {value} {unit_from} to {unit_to} {self.bot.get_emojis('loading_emoji')}")
        converted_value, unit_from, unit_to = unit_conversion(value, unit_from, unit_to)
        embed = discord.Embed(
            title="Unit Conversion",
            description=f"{value} {unit_from} is equal to {converted_value} {unit_to}",
            colour=discord.Colour.blurple(),
            timestamp=utcnow(),
        )
        embed.add_field(name="Result", value=f"{converted_value} {unit_to}")
        embed.add_field(name="From", value=f"{unit_from}")
        embed.add_field(name="To", value=f"{unit_to}")
        await ctx.edit(content="", embed=embed)

    @discord.slash_command(
        integration_types={
        discord.IntegrationType.guild_install,
        discord.IntegrationType.user_install,
        },
        name="qr-code",
        description="Generate a QR code",
    )
    @discord.option(
        "text",
        description="The text to encode",
        type=str,
        required=True
    )
    @discord.option(
        name="output",
        description="The output format",
        type=str,
        required=False,
        choices=["image", "text"],
        default="text"
    )

    async def qr_code_command(self, ctx: Context, text: str, output: str = "image"):
        await ctx.defer()
        await ctx.respond(content = f"Generating QR code {self.bot.get_emojis('loading_emoji')}")
        if output == "image":
            qr_code_image = qr_code_image_generator(text)
            await ctx.edit(content = "", file=discord.File(qr_code_image))
            os.remove(qr_code_image)
        if output == "text":
            qr_code_text = qr_code_text_generator(text)
            await ctx.edit(content = f"```\n{qr_code_text}\n```")

    @discord.slash_command(
        integration_types={
        discord.IntegrationType.guild_install,
        discord.IntegrationType.user_install,
        },
        name="timestamp",
        description="Convert a timestamp to a readable format",
    )
    @discord.option(
        "date-time",
        description="The timestamp to convert",
        type=str,
        required=False
    )
    @discord.option(
        name="format",
        description="The format to convert the timestamp to",
        type=str,
        required=True,
        choices=["relative", "short time", "long time", "short date", "long date", "long date with short time", "long date with day of the week"]
    )
    async def timestamp_command(self, ctx: Context, time_string: str = None, format: str = "relative"):
        await ctx.defer()
        await ctx.respond(content = f"Converting timestamp to a readable format {self.bot.get_emojis('loading_emoji')}")
        converted_timestamp = await timecode_convert(time_string, format)
        if converted_timestamp is None:
            raise discord.errors.ApplicationCommandError("Invalid timestamp")
        return await ctx.edit(content = f"Converted timestamp: {converted_timestamp}")
    

def setup(bot):
    bot.add_cog(Utilities(bot))

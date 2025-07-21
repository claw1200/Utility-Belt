import discord
from core import Cog, Context
import concurrent.futures
import random
from gradio_client import Client as GradioClient
import asyncio
import os
import requests
import json

def ai_image_gen(prompt, enhancer, img2img, img_seed, img_strength, img_steps): # blocking function
    if prompt == None:
        # read config.json
        try:
            with open("config.json", "r") as f:
                config = f.read()
                config = json.loads(config)
                prompt = config["ai_image_default_prompt"]
        except FileNotFoundError:
            prompt = "A beautiful landscape with a sunset"

    if img2img != None:
        try:
            response = requests.get(img2img)
            response.raise_for_status()
        except Exception as e:
            raise discord.errors.ApplicationCommandError(e)

    # with aiofiles.open("config/wordblacklist.json", "r") as f:
    #     banned_words = f.read()
    #     banned_words = json.loads(banned_words)["words"]
    # for word in banned_words:
    #     if word in prompt.lower():
    #         return None

    if enhancer == None:
        enhancer = "none"
    
    enhancer_prompts = {
    "none": f"{prompt}",

    "digital painting": f"{prompt}, glow effects, godrays, Hand drawn, render, 8k, octane render, cinema 4d, blender, dark, atmospheric 4k ultra detailed, cinematic, Sharp focus, big depth of field, Masterpiece, colors, 3d octane render, 4k, concept art, trending on artstation, hyperrealistic, Vivid colors, extremely detailed CG unity 8k wallpaper, trending on CGSociety, Intricate, High Detail, dramatic",
    
    "indie game": f"{prompt}, Indie game art, Vector Art, Borderlands style, Arcane style, Cartoon style, Line art, Distinct features, Hand drawn, Technical illustration, Graphic design, Vector graphics, High contrast, Precision artwork, Linear compositions, Scalable artwork, Digital art, cinematic sensual, Sharp focus, humorous illustration, big depth of field, Masterpiece, trending on artstation, Vivid colors, trending on ArtStation, trending on CGSociety, Intricate, Low Detail, dramatic",
    
    "photo": f"{prompt}, Photorealistic, Hyperrealistic, Hyperdetailed, analog style, soft lighting, subsurface scattering, realistic, heavy shadow, masterpiece, best quality, ultra realistic, 8k, golden ratio, Intricate, High Detail, film photography, soft focus",
    
    "film noir": f"{prompt}, (b&w, Monochromatic, Film Photography:1.3),  Photorealistic, Hyperrealistic, Hyperdetailed, film noir, analog style, soft lighting, subsurface scattering, realistic, heavy shadow, masterpiece, best quality, ultra realistic, 8k, golden ratio, Intricate, High Detail, film photography, soft focus",
    
    "isometric room": f"{prompt}, Tiny cute isometric in a cutaway box, soft smooth lighting, soft colors, 100mm lens, 3d blender render",
    
    "space hologram": f"{prompt}, hologram floating in space, a vibrant digital illustration, dribble, quantum wavetracing, black background, bechance hd",
    
    "cute creature": f"{prompt}, 3d fluffy, closeup cute and adorable, cute big circular reflective eyes, long fuzzy fur, Pixar render, unreal engine cinematic smooth, intricate detail, cinematic",
    
    "realistic portrait": f"{prompt}, RAW candid cinema, 16mm, color graded portrait 400 film, remarkable color, ultra realistic, textured skin, remarkable detailed pupils, realistic dull skin noise, visible skin detail, skin fuzz, dry skin, shot with cinematic camera",
    
    "realistic landscape": f"long shot scenic professional photograph of {prompt}, perfect viewpoint, highly detailed, wide-angle lens, hyper realistic, with dramatic sky, polarizing filter, natural lighting, vivid colors, everything in sharp focus, HDR, UHD, 64K",
    }

    prompt = enhancer_prompts.get(enhancer.lower(), prompt)

    if img_seed == None:
        img_seed = random.randint(1,999999999)

    if img_strength == None:
        img_strength = 0.7

    if img_steps == None:
        img_steps = 3

    ai_api_url = "diffusers/unofficial-SDXL-Turbo-i2i-t2i"

    client = GradioClient(ai_api_url, output_dir="temp/")
    result = client.predict(img2img, f"{prompt}", img_strength, img_steps, img_seed, api_name="/predict")
    result = discord.File(fp=result, filename="image.png")
    return result

async def unblocked_ai_image_gen(executor, prompt, enhancer, img2img, img_seed, img_strength, img_steps):
    loop = asyncio.get_running_loop()
    future = loop.run_in_executor(executor, ai_image_gen, prompt, enhancer, img2img, img_seed, img_strength, img_steps)
    result = await asyncio.ensure_future(future)
    return result


class Ai(Cog):
    """Ai Commands"""

    @discord.slash_command(
        integration_types={
        discord.IntegrationType.guild_install,
        discord.IntegrationType.user_install,
        },
        name="imagine",
        description="AI generate an image with SDXLTurbo"
    )
    # async def ai_image_gen(prompt, enhancer, img2img, img_seed, img_strength, img_steps):
    @discord.option(
        "text",
        description="The text to generate an image with",
        type=str,
        required=False,
    )
    @discord.option(
        "enhancer",
        description="The enhancer to use",
        type=str,
        choices=["None", "Digital Painting", "Indie Game", "Photo", "Film Noir", "Isometric Room", "Space Hologram", "Cute Creature", "Realistic Portrait", "Realistic Landscape"],
        required=False,
        default="None",
    )
    @discord.option(
        "img2img",
        description="The URL for the image to image model to use",
        type=str,
        required=False,
        default=None,
    )
    @discord.option(
        "seed",
        description="The seed for the image",
        type=int,
        required=False,
        default=None,
    )
    @discord.option(
        "strength",
        description="The strength of the image",
        type=float,
        required=False,
        default=0.7,
    )
    @discord.option(
        "steps",
        description="The number of steps to take",
        type=int,
        choices=[1, 2, 3, 4, 5, 6, 7, 8],
        required=False,
        default=3,
    )
    async def ai_image_gen_command(self, ctx: Context, prompt: str = None, enhancer: str = "None", img2img: str = None, seed: int = None, strength: int = 0.7, steps: int = 3):
        """AI generate an image with SDXLTurbo using ai_image_gen"""
        await ctx.defer()
        await ctx.respond(content = f"Generating image with SDXLTurbo {self.bot.get_emojis('loading_emoji')}")
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        file = await (unblocked_ai_image_gen(executor, prompt, enhancer, img2img, seed, strength, steps))
        await ctx.edit(content = f"", file=file)
        os.remove(file.fp.name)
        # also remove the parent directory of the file if it is empty
        os.rmdir(os.path.dirname(file.fp.name))
        


def setup(bot):
    #bot.add_cog(Ai(bot))
    pass


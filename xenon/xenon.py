import discord
from redbot.core import commands
import json
import os
import uuid

class ServerTemplate:
    def __init__(self, channels, roles):
        self.channels = channels
        self.roles = roles

class Xenon(commands.Cog):
    """A cog that copies servers as templates and applies them to other servers."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def savet(self, ctx):
        """Saves the current server's structure as a template."""
        guild = ctx.guild
        channels = []
        roles = []

        # Save channels
        for channel in guild.channels:
            channels.append({
                'name': channel.name,
                'type': str(channel.type),
                'position': channel.position,
                'permissions': {str(role.id): perm.pair() for role, perm in channel.overwrites.items()}
            })

        # Save roles
        for role in guild.roles:
            roles.append({
                'name': role.name,
                'permissions': role.permissions.value,
                'position': role.position,
                'color': role.color.value,
                'hoist': role.hoist,
                'mentionable': role.mentionable
            })

        template = ServerTemplate(channels, roles)
        template_id = str(uuid.uuid4())
        with open(f'templates/{template_id}.json', 'w') as f:
            json.dump(template.__dict__, f)

        await ctx.send(f'Template saved with ID: {template_id}')

    @commands.command()
    async def loadt(self, ctx, template_id: str):
        """Loads a template and applies it to the current server."""
        guild = ctx.guild

        # Load template
        try:
            with open(f'templates/{template_id}.json', 'r') as f:
                template_data = json.load(f)
        except FileNotFoundError:
            await ctx.send('Template not found.')
            return

        template = ServerTemplate(**template_data)

        # Clear existing channels and roles
        for channel in guild.channels:
            await channel.delete()
        for role in guild.roles:
            if role != guild.default_role:
                await role.delete()

        # Create roles
        role_map = {}
        for role_data in template.roles:
            role = await guild.create_role(
                name=role_data['name'],
                permissions=discord.Permissions(role_data['permissions']),
                color=discord.Color(role_data['color']),
                hoist=role_data['hoist'],
                mentionable=role_data['mentionable']
            )
            role_map[role_data['name']] = role

        # Create channels
        for channel_data in template.channels:
            overwrites = {
                role_map[role_name]: discord.PermissionOverwrite(**dict(zip(['read_messages', 'send_messages'], perm)))
                for role_name, perm in channel_data['permissions'].items()
            }
            if channel_data['type'] == 'text':
                await guild.create_text_channel(
                    name=channel_data['name'],
                    position=channel_data['position'],
                    overwrites=overwrites
                )
            elif channel_data['type'] == 'voice':
                await guild.create_voice_channel(
                    name=channel_data['name'],
                    position=channel_data['position'],
                    overwrites=overwrites
                )

        await ctx.send('Template applied successfully.')

def setup(bot):
    bot.add_cog(Xenon(bot))

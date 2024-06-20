import discord
from redbot.core import commands, Config
from redbot.core.bot import Red

class FeatureRequest(commands.Cog):
    """Cog to handle feature requests."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567892, force_registration=True)
        default_global = {
            "request_channel": None,
            "requests": {}
        }
        self.config.register_global(**default_global)

    @commands.is_owner()
    @commands.group(aliases=["fr"])
    async def frequest(self, ctx: commands.Context):
        """Base command for feature requests."""
        pass

    @frequest.command()
    async def submit(self, ctx: commands.Context, *, feature: str):
        """Request a new feature for the bot."""
        request_channel_id = await self.config.request_channel()
        if not request_channel_id:
            await ctx.send("Request channel is not set. Please ask the bot owner to set it using the frequest channel command.")
            return

        request_channel = self.bot.get_channel(request_channel_id)
        if not request_channel:
            await ctx.send("Request channel not found. Please ask the bot owner to set it again using the frequest channel command.")
            return

        embed = discord.Embed(
            title="Feature Request",
            description=f"Feature requested by {ctx.author.mention}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Feature", value=feature, inline=True)
        embed.add_field(name="Status", value="Pending", inline=True)

        message = await request_channel.send(embed=embed)
        request_data = {
            "requester_id": ctx.author.id,
            "feature": feature,
            "status": "pending",
            "message_id": message.id
        }

        async with self.config.requests() as requests:
            requests[message.id] = request_data

    @frequest.command()
    @commands.is_owner()
    async def accept(self, ctx: commands.Context, *, feature: str):
        """Accept a feature request."""
        async with self.config.requests() as requests:
            request_data = next((req for req in requests.values() if req["feature"] == feature and req["status"] == "pending"), None)
            if not request_data:
                await ctx.send(f"No pending feature request found with feature: {feature}")
                return

            request_data["status"] = "accepted"
            requester = self.bot.get_user(request_data["requester_id"])
            if requester:
                try:
                    await requester.send(embed=discord.Embed(
                        title="Feature Request Accepted",
                        description=f"Your feature request of `{feature}` was accepted.",
                        color=discord.Color.green()
                    ))
                except discord.Forbidden:
                    pass

            request_channel = self.bot.get_channel(await self.config.request_channel())
            if request_channel:
                try:
                    message = await request_channel.fetch_message(request_data["message_id"])
                    embed = message.embeds[0]
                    embed.set_field_at(1, name="Status", value="Accepted", inline=True)
                    embed.color = discord.Color.green()
                    await message.edit(embed=embed)
                except discord.NotFound:
                    await ctx.send(f"Message with ID {request_data['message_id']} not found in the request channel.")
                except discord.Forbidden:
                    await ctx.send("I don't have permission to edit the message in the request channel.")

            await ctx.send(f"Feature request with feature `{feature}` has been accepted.")

            # Send update embed
            update_embed = discord.Embed(
                title="Request Updated",
                color=discord.Color.green()
            )
            update_embed.add_field(name="Request", value=feature, inline=True)
            update_embed.add_field(name="Status", value="Accepted", inline=True)
            await request_channel.send(embed=update_embed)

    @frequest.command()
    @commands.is_owner()
    async def deny(self, ctx: commands.Context, *, feature: str):
        """Deny a feature request."""
        async with self.config.requests() as requests:
            request_data = next((req for req in requests.values() if req["feature"] == feature and req["status"] == "pending"), None)
            if not request_data:
                await ctx.send(f"No pending feature request found with feature: {feature}")
                return

            request_data["status"] = "denied"
            requester = self.bot.get_user(request_data["requester_id"])
            if requester:
                try:
                    await requester.send(embed=discord.Embed(
                        title="Feature Request Denied",
                        description=f"Your feature request of `{feature}` was denied.",
                        color=discord.Color.red()
                    ))
                except discord.Forbidden:
                    pass

            request_channel = self.bot.get_channel(await self.config.request_channel())
            if request_channel:
                try:
                    message = await request_channel.fetch_message(request_data["message_id"])
                    embed = message.embeds[0]
                    embed.set_field_at(1, name="Status", value="Denied", inline=True)
                    embed.color = discord.Color.red()
                    await message.edit(embed=embed)
                except discord.NotFound:
                    await ctx.send(f"Message with ID {request_data['message_id']} not found in the request channel.")
                except discord.Forbidden:
                    await ctx.send("I don't have permission to edit the message in the request channel.")

            await ctx.send(f"Feature request with feature `{feature}` has been denied.")

            # Send update embed
            update_embed = discord.Embed(
                title="Request Updated",
                color=discord.Color.red()
            )
            update_embed.add_field(name="Request", value=feature, inline=True)
            update_embed.add_field(name="Status", value="Denied", inline=True)
            await request_channel.send(embed=update_embed)

    @frequest.command()
    @commands.is_owner()
    async def consider(self, ctx: commands.Context, *, feature: str):
        """Consider a feature request."""
        async with self.config.requests() as requests:
            request_data = next((req for req in requests.values() if req["feature"] == feature and req["status"] == "pending"), None)
            if not request_data:
                await ctx.send(f"No pending feature request found with feature: {feature}")
                return

            request_data["status"] = "considering"
            requester = self.bot.get_user(request_data["requester_id"])
            if requester:
                try:
                    await requester.send(embed=discord.Embed(
                        title="Feature Request Considering",
                        description=f"Your feature request of `{feature}` is being considered.",
                        color=discord.Color.blue()
                    ))
                except discord.Forbidden:
                    pass

            request_channel = self.bot.get_channel(await self.config.request_channel())
            if request_channel:
                try:
                    message = await request_channel.fetch_message(request_data["message_id"])
                    embed = message.embeds[0]
                    embed.set_field_at(1, name="Status", value="Considering", inline=True)
                    embed.color = discord.Color.blue()
                    await message.edit(embed=embed)
                except discord.NotFound:
                    await ctx.send(f"Message with ID {request_data['message_id']} not found in the request channel.")
                except discord.Forbidden:
                    await ctx.send("I don't have permission to edit the message in the request channel.")

            await ctx.send(f"Feature request with feature `{feature}` is being considered.")

            # Send update embed
            update_embed = discord.Embed(
                title="Request Updated",
                color=discord.Color.blue()
            )
            update_embed.add_field(name="Request", value=feature, inline=True)
            update_embed.add_field(name="Status", value="Considering", inline=True)
            await request_channel.send(embed=update_embed)

    @frequest.command()
    async def status(self, ctx: commands.Context, *, feature: str):
        """Check the status of your feature request."""
        async with self.config.requests() as requests:
            request_data = next((req for req in requests.values() if req["feature"] == feature and req["requester_id"] == ctx.author.id), None)
            if not request_data:
                await ctx.send(f"No feature request found with feature: {feature}")
                return

            status = request_data["status"]
            await ctx.author.send(embed=discord.Embed(
                title="Feature Request Status",
                description=f"Your request status is: **{status.capitalize()}**",
                color=discord.Color.blue()
            ))

    @frequest.command()
    @commands.is_owner()
    async def channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the channel for feature requests."""
        await self.config.request_channel.set(channel.id)
        await ctx.send(f"Request channel set to: {channel.mention}")

def setup(bot: Red):
    bot.add_cog(FeatureRequest(bot))

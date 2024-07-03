import discord
from redbot.core import commands, Config
from redbot.core.bot import Red
from datetime import datetime, timedelta
import re
import uuid

class AdWarn(commands.Cog):
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)  # Replace with a unique identifier
        self.config.register_guild(warn_channel=None, thresholds={})
        self.config.register_member(warnings=[], untimeout_time=None)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def adwarn(self, ctx, user: discord.Member, *, reason: str):
        """Warn a user and send an embed to the default warning channel."""
        warn_channel_id = await self.config.guild(ctx.guild).warn_channel()
        if warn_channel_id:
            warn_channel = self.bot.get_channel(warn_channel_id)
            if warn_channel:
                # Store the warning with a UUID
                warnings = await self.config.member(user).warnings()
                warning_time = datetime.utcnow().isoformat()
                warning_id = str(uuid.uuid4())
                warnings.append({
                    "id": warning_id,
                    "reason": reason,
                    "moderator": ctx.author.id,
                    "time": warning_time,
                    "channel": ctx.channel.id
                })
                await self.config.member(user).warnings.set(warnings)

                # Create the embed message
                embed = discord.Embed(title="You were warned!", color=discord.Color.red())
                embed.add_field(name="User", value=user.mention, inline=True)
                embed.add_field(name="In", value=ctx.channel.mention, inline=True)
                embed.add_field(name="Reason", value=reason, inline=False)
                embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
                embed.add_field(name="Time", value=warning_time, inline=False)
                embed.set_footer(text=f"Total warnings: {len(warnings)}")

                # Send the embed to the specified warning channel
                await warn_channel.send(embed=embed)

                # Send plain text message to the warning channel
                await warn_channel.send(f"{user.mention}")

                # Send confirmation embed to the command issuer
                confirmation_embed = discord.Embed(
                    title="Warning Issued",
                    description=f"{user.mention} has been warned for: {reason} in {ctx.channel.mention}",
                    color=discord.Color.green()
                )
                confirmation_message = await ctx.send(embed=confirmation_embed)
                await confirmation_message.delete(delay=3)

                # Check thresholds and take action if necessary
                await self.check_thresholds(ctx, user, len(warnings))
            else:
                error_embed = discord.Embed(
                    title="Error 404",
                    description="Warning channel not found. Please set it again using `[p]warnset channel`.",
                    color=discord.Color.red()
                )
                error_message = await ctx.send(embed=error_embed)
                await error_message.delete(delay=3)
        else:
            error_embed = discord.Embed(
                title="Error 404",
                description="No warning channel has been set. Please set it using `[p]warnset channel`.",
                color=discord.Color.red()
            )
            error_message = await ctx.send(embed=error_embed)
            await error_message.delete(delay=3)

        # Delete the command message after 3 seconds
        await ctx.message.delete(delay=3)

    async def check_thresholds(self, ctx, user, warning_count):
        thresholds = await self.config.guild(ctx.guild).thresholds()

        for threshold_id, threshold in thresholds.items():
            if threshold["count"] == warning_count:
                action = threshold["action"]
                if action == "kick":
                    await ctx.guild.kick(user, reason="Reached warning threshold")
                    await ctx.send(f"{user.mention} has been kicked for reaching {warning_count} warnings.")
                elif action == "ban":
                    await ctx.guild.ban(user, reason="Reached warning threshold")
                    await ctx.send(f"{user.mention} has been banned for reaching {warning_count} warnings.")
                elif action.startswith("mute"):
                    timeout_duration = self.parse_duration(action.split(" ")[1]) if " " in action else None

                    await self.timeout_user(ctx, user, timeout_duration)
                    await ctx.send(f"{user.mention} has been timed out for reaching {warning_count} warnings.")
                    if timeout_duration:
                        await self.schedule_untimeout(ctx, user, timeout_duration)

                # Add more actions as needed

    def parse_duration(self, duration_str):
        """Parse a duration string and return the duration in minutes."""
        match = re.match(r"(\d+)([mh])", duration_str)
        if match:
            value, unit = match.groups()
            value = int(value)
            if unit == "h":
                return value * 60  # Convert hours to minutes
            elif unit == "m":
                return value  # Minutes
        return None

    async def timeout_user(self, ctx, user: discord.Member, duration: int = None):
        if duration:
            timeout_until = datetime.utcnow() + timedelta(minutes=duration)
            await user.edit(timed_out_until=timeout_until, reason="Reached warning threshold")
            await self.config.member(user).untimeout_time.set(timeout_until.isoformat())

            # Create and send embed with timeout details
            timeout_hours = duration / 60
            embed = discord.Embed(
                title="User Timed Out",
                description=f"{user.mention} has been timed out for {timeout_hours:.2f} hours.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
        else:
            await user.edit(timed_out_until=None, reason="Reached warning threshold")

    async def schedule_untimeout(self, ctx, user, duration):
        untimeout_time = datetime.utcnow() + timedelta(minutes=duration)
        await self.config.member(user).untimeout_time.set(untimeout_time.isoformat())
        await ctx.send(f"{user.mention} will be untimed out in {duration / 60:.2f} hours.")

    @commands.Cog.listener()
    async def on_ready(self):
        await self.check_untimeout_times()

    async def check_untimeout_times(self):
        for guild in self.bot.guilds:
            for member in guild.members:
                untimeout_time = await self.config.member(member).untimeout_time()
                if untimeout_time:
                    untimeout_time = datetime.fromisoformat(untimeout_time)
                    if datetime.utcnow() >= untimeout_time:
                        await self.untimeout_user(member)
                        await self.config.member(member).untimeout_time.clear()

    async def untimeout_user(self, user: discord.Member):
        await user.edit(timed_out_until=None, reason="Timeout duration expired")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def removewarn(self, ctx, user: discord.Member, warning_id: str):
        """Remove a specific warning from a user by its UUID."""
        warnings = await self.config.member(user).warnings()
        warning_to_remove = next((warning for warning in warnings if warning["id"] == warning_id), None)

        if warning_to_remove:
            warnings.remove(warning_to_remove)
            await self.config.member(user).warnings.set(warnings)

            warn_channel_id = await self.config.guild(ctx.guild).warn_channel()
            if warn_channel_id:
                warn_channel = self.bot.get_channel(warn_channel_id)
                if warn_channel:
                    # Create the embed message
                    embed = discord.Embed(title="AdWarn Removed", color=discord.Color.green())
                    embed.add_field(name="Warning", value=warning_to_remove["reason"], inline=False)
                    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
                    embed.add_field(name="Removed Time", value=datetime.utcnow().isoformat(), inline=True)
                    embed.set_footer(text=f"Total warnings: {len(warnings)}")

                    # Send the embed to the specified warning channel
                    await warn_channel.send(embed=embed)
                else:
                    error_embed = discord.Embed(
                        title="Error 404",
                        description="Warning channel not found. Please set it again using `[p]warnset channel`.",
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=error_embed)
            else:
                error_embed = discord.Embed(
                    title="Error 404",
                    description="No warning channel has been set. Please set it using `[p]warnset channel`.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=error_embed)
        else:
            error_embed = discord.Embed(
                title="Error 404",
                description=f"Warning with ID {warning_id} not found.",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def warncount(self, ctx, user: discord.Member):
        """Get the total number of warnings a user has."""
        warnings = await self.config.member(user).warnings()
        embed = discord.Embed(
            title="Warning Count",
            description=f"{user.mention} has {len(warnings)} warnings.",
            color=discord.Color.blue()
        )

        for warning in warnings:
            embed.add_field(
                name=f"Warning ID: {warning['id']}",
                value=f"Reason: {warning['reason']}\nModerator: <@{warning['moderator']}>\nTime: {warning['time']}",
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clearwarns(self, ctx, user: discord.Member):
        """Clear all warnings for a user."""
        await self.config.member(user).warnings.set([])
        warn_channel_id = await self.config.guild(ctx.guild).warn_channel()
        if warn_channel_id:
            warn_channel = self.bot.get_channel(warn_channel_id)
            if warn_channel:
                # Create the embed message
                embed = discord.Embed(title="All Warnings Cleared", color=discord.Color.green())
                embed.add_field(name="User", value=user.mention, inline=True)
                embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
                embed.add_field(name="Cleared Time", value=datetime.utcnow().isoformat(), inline=True)

                # Send the embed to the specified warning channel
                await warn_channel.send(embed=embed)
            else:
                error_embed = discord.Embed(
                    title="Error 404",
                    description="Warning channel not found. Please set it again using `[p]warnset channel`.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=error_embed)
        else:
            error_embed = discord.Embed(
                title="Error 404",
                description="No warning channel has been set. Please set it using `[p]warnset channel`.",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def unadwarn(self, ctx, user: discord.Member):
        """Clear the most recent warning for a user."""
        warnings = await self.config.member(user).warnings()
        if warnings:
            removed_warning = warnings.pop()
            await self.config.member(user).warnings.set(warnings)

            warn_channel_id = await self.config.guild(ctx.guild).warn_channel()
            if warn_channel_id:
                warn_channel = self.bot.get_channel(warn_channel_id)
                if warn_channel:
                    # Create the embed message
                    embed = discord.Embed(title="Most Recent AdWarn Removed", color=discord.Color.green())
                    embed.add_field(name="Warning", value=removed_warning["reason"], inline=False)
                    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
                    embed.add_field(name="Removed Time", value=datetime.utcnow().isoformat(), inline=True)
                    embed.set_footer(text=f"Total warnings: {len(warnings)}")

                    # Send the embed to the specified warning channel
                    await warn_channel.send(embed=embed)
                else:
                    error_embed = discord.Embed(
                        title="Error 404",
                        description="Warning channel not found. Please set it again using `[p]warnset channel`.",
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=error_embed)
            else:
                error_embed = discord.Embed(
                    title="Error 404",
                    description="No warning channel has been set. Please set it using `[p]warnset channel`.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=error_embed)
        else:
            error_embed = discord.Embed(
                title="Error 404",
                description=f"{user.mention} has no warnings.",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)

    @commands.group()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def warnset(self, ctx):
        """Settings for the warning system."""
        pass

    @warnset.command()
    async def channel(self, ctx, channel: discord.TextChannel):
        """Set the default channel for warnings."""
        await self.config.guild(ctx.guild).warn_channel.set(channel.id)
        embed = discord.Embed(
            title="Warning Channel Set",
            description=f"Warning channel has been set to {channel.mention}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @warnset.command()
    async def show(self, ctx):
        """Show the current warning channel and thresholds."""
        channel_id = await self.config.guild(ctx.guild).warn_channel()
        thresholds = await self.config.guild(ctx.guild).thresholds()

        embed = discord.Embed(
            title="Warning System Configuration",
            color=discord.Color.blue()
        )

        if channel_id:
            channel = self.bot.get_channel(channel_id)
            embed.add_field(name="Current Warning Channel", value=channel.mention, inline=False)
        else:
            embed.add_field(name="Current Warning Channel", value="Not set", inline=False)

        if thresholds:
            threshold_list = "\n".join([f"{threshold_id}: {threshold['count']} warnings -> {threshold['action']}" for threshold_id, threshold in thresholds.items()])
            embed.add_field(name="Warning Thresholds", value=threshold_list, inline=False)
        else:
            embed.add_field(name="Warning Thresholds", value="No thresholds set", inline=False)

        await ctx.send(embed=embed)

    @warnset.command()
    async def threshold(self, ctx, warning_count: int, action: str, duration: str = None):
        """Set an action for a specific warning count threshold."""
        valid_actions = ["kick", "ban", "mute"]  # Add more actions as needed
        if action not in valid_actions and not action.startswith("mute"):
            await ctx.send(f"Invalid action. Valid actions are: {', '.join(valid_actions)} or 'mute <duration>'")
            return

        if action == "mute" and duration:
            parsed_duration = self.parse_duration(duration)
            if parsed_duration is None:
                await ctx.send("Invalid duration format. Use 'Xm' for minutes or 'Xh' for hours.")
                return
            action = f"mute {parsed_duration}"

        thresholds = await self.config.guild(ctx.guild).thresholds()
        threshold_id = str(uuid.uuid4())
        thresholds[threshold_id] = {
            "count": warning_count,
            "action": action
        }
        await self.config.guild(ctx.guild).thresholds.set(thresholds)
        await ctx.send(f"Set action '{action}' for reaching {warning_count} warnings.")

    @warnset.command()
    async def delthreshold(self, ctx, threshold_id: str):
        """Delete a specific warning count threshold by its UUID."""
        thresholds = await self.config.guild(ctx.guild).thresholds()
        if threshold_id in thresholds:
            del thresholds[threshold_id]
            await self.config.guild(ctx.guild).thresholds.set(thresholds)
            await ctx.send(f"Deleted threshold with ID {threshold_id}.")
        else:
            await ctx.send(f"No threshold set with ID {threshold_id}.")

"""
Example system skill: Echo
Simple echo functionality for testing
"""

SKILL_NAME = "echo"
SKILL_DESCRIPTION = "Echo messages back to user"
SKILL_CATEGORY = "utility"
SKILL_VERSION = "1.0.0"
SKILL_AUTHOR = "Alex-Nano-Bot System"
SKILL_COMMANDS = ["/echo"]


async def handle_command(command: str, args: list, message, bot):
    """Handle echo command"""
    if command == "echo":
        return await echo_message(message, args)
    return None


async def echo_message(message, args):
    """Echo the message back"""
    if not args:
        await message.reply(
            "📢 <b>Echo</b>\n\n"
            "Usage: <code>/echo Hello World</code>\n\n"
            "I'll repeat whatever you say!"
        )
        return
    
    text = " ".join(args)
    
    await message.reply(
        f"📢 <b>Echo:</b>\n\n"
        f"<i>{text}</i>"
    )


def setup_handlers():
    """Setup command handlers for this skill"""
    return {
        "echo": handle_command
    }

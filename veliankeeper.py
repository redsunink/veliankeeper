from typing import Literal, Optional
import discord
from discord.ext.commands import Greedy, Context
from discord.ext import commands
from discord.ui import View, Select
from discord import app_commands
from discord import Embed
import scraphauler #Import scraper
import db_manager #Import database management
import json
import logging
import traceback
import random
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#--Init--
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Database health check
if db_manager.check_database_health():
    logger.info("Database health check passed. Bot initialization continuing.")
else:
    logger.error("Database health check failed. Please resolve the issues and restart the bot.")
    exit(1)  # Exit the script if the database check fails

with open('vkeeper_config.json', 'r') as config_file:
    config = json.load(config_file)

with open('vkeeper_quotes.json', 'r') as f:
    quotes = json.load(f)

verification_roles = config['verification_roles']
command_use_roles = config['command_use_roles']
critical_command_roles = config['critical_command_roles']
bot_token = config['bot_token']

#Help section dictionary
def load_help_manual():
    with open('vkeeper_manual.json', 'r') as f:
        return json.load(f)
help_manual_data = load_help_manual()

# Define a check for users with multiple possible verification roles
def has_verification_role():
    async def predicate(interaction: discord.Interaction):
        allowed_roles = verification_roles  
        user_roles = [role.name for role in interaction.user.roles]
        
        # Check if the user has any of the allowed roles
        if any(role in allowed_roles for role in user_roles):
            return True
        else:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return False
    return app_commands.check(predicate)

#Define a check with user roles who can execute commands
def has_command_use_role():
    async def predicate(interaction: discord.Interaction):
        allowed_roles = command_use_roles  
        user_roles = [role.name for role in interaction.user.roles]
        
        # Check if the user has any of the allowed roles
        if any(role in allowed_roles for role in user_roles):
            return True
        else:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return False
    return app_commands.check(predicate)

#Define a check with user roles who can execute critical commands
def has_critical_command_use_role():
    async def predicate(interaction: discord.Interaction):
        allowed_roles = critical_command_roles  
        user_roles = [role.name for role in interaction.user.roles]
        
        # Check if the user has any of the allowed roles
        if any(role in allowed_roles for role in user_roles):
            return True 
        else:
            await interaction.response.send_message("This is a critical command. You don't have permission to use it.", ephemeral=True)
            return False
    return app_commands.check(predicate)    

def task_embed(task):
    embed = discord.Embed(
        title=f"Task: {task['amount']} x {task['item_name']} to {task['stockpile_name']}",
        description=f"Task created by <@{task['created_by']}>",
        color=discord.Color.blue()
    )
    assigned_users_list = task['assigned_users'] if isinstance(task['assigned_users'], list) else json.loads(task['assigned_users'])
    formatted_assigned_users = ", ".join([f"<@{user_id}>" for user_id in assigned_users_list]) if assigned_users_list else "None"
    embed.add_field(name="Status", value=task['status'].capitalize(), inline=True)
    embed.add_field(name="Progress", value=f"{task['current_amount']} / {task['amount']}", inline=True)
    embed.add_field(name="Facility", value=task['facility_name'], inline=True)
    embed.add_field(name="Stockpile", value=task['stockpile_name'], inline=True)
    embed.add_field(name="Assigned Users", value=formatted_assigned_users, inline=False)
    embed.set_thumbnail(url=task['thumbnail'])
    random_quote = random.choice(quotes['task_quotes'])
    embed.set_footer(text=f"Task ID: {task['id']} | {random_quote}")
    return embed


def custom_task_embed(task):
    embed = discord.Embed(
        title=f"Task: {task['task_header']}",
        description=f"Task created by <@{task['created_by']}>",
        color=discord.Color.blue()
    )
    assigned_users_list = task['assigned_users'] if isinstance(task['assigned_users'], list) else json.loads(task['assigned_users'])
    formatted_assigned_users = ", ".join([f"<@{user_id}>" for user_id in assigned_users_list]) if assigned_users_list else "None"
    embed.add_field(name="Description", value=task['task_description'], inline=False)
    embed.add_field(name="Location", value=task['task_location'], inline=False)
    embed.add_field(name="Assigned Users", value=formatted_assigned_users, inline=False)
    embed.set_footer(text=f"Custom Task ID: {task['id']}")
    return embed


class PaginationView(discord.ui.View):

	def __init__(self, data):
		super().__init__(timeout=None)
		self.data = data
		self.current_page = 1
		self.sep = 5

	async def send (self, interaction: discord.Interaction):
		self.message = await interaction.response.send_message(embed=self.create_help_embed(), view=self)
		
	def create_help_embed(self):
		embed = discord.Embed(title="Velian Keeper User Manual")
		start = (self.current_page - 1) * self.sep
		end =  start + self.sep
		for item in self.data[start:end]:
			command = item['command']
			description = item['description']
			embed.add_field(name=command, value=description, inline=False)
			
		embed.set_footer(text=f"Page {self.current_page}/{self.max_pages}")
		return embed
		
	async def update_message(self, interaction: discord.Interaction):
		await interaction.response.edit_message(embed=self.create_help_embed(), view=self)
		
	@property
	def max_pages(self):
		return -(-len(self.data) // self.sep)  # Ceiling division
		
	@discord.ui.button(label="First", style=discord.ButtonStyle.primary)
	async def first_button(self, interaction: discord.Interaction, button: discord.ui.Button):
		self.current_page = 1
		await self.update_message(interaction)

	@discord.ui.button(label="Previous", style=discord.ButtonStyle.primary)
	async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
		self.current_page = max(1, self.current_page - 1)
		await self.update_message(interaction)

	@discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
	async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
		self.current_page = min(self.max_pages, self.current_page + 1)
		await self.update_message(interaction)

	@discord.ui.button(label="Last", style=discord.ButtonStyle.primary)
	async def last_button(self, interaction: discord.Interaction, button: discord.ui.Button):
		self.current_page = self.max_pages
		await self.update_message(interaction)

class TaskManagerView(discord.ui.View):
    def __init__(self, task_id):
        super().__init__(timeout=None)
        self.task_id = task_id
        # Add a custom ID to the view
        self.custom_id = f"task_manager_{task_id}"
        
    async def update_message(self, interaction: discord.Interaction):
        updated_task = db_manager.get_task(self.task_id)
        updated_embed = task_embed(updated_task)
        await interaction.response.edit_message(embed=updated_embed, view=self)

    @discord.ui.button(label="Pick task", style=discord.ButtonStyle.green, custom_id="sign_up")
    async def sign_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        task = db_manager.get_task(self.task_id)
        assigned_users = json.loads(task['assigned_users'])
        
        if user_id in assigned_users:
            # User is already assigned, so remove them
            assigned_users.remove(user_id)
            action = "dropped from"
            button.label = "Pick task"
            button.style = discord.ButtonStyle.green
        else:
            # User is not assigned, so add them
            assigned_users.append(user_id)
            action = "signed up for"
            button.label = "Drop Task"
            button.style = discord.ButtonStyle.gray
        
        db_manager.update_task_assigned_users(self.task_id, json.dumps(assigned_users))
        
        # Update the embed with the new user list
        await self.update_message(interaction)
        
        await interaction.followup.send(f"You've been {action} the task!", ephemeral=True)

    @discord.ui.button(label="Submit", style=discord.ButtonStyle.blurple, custom_id="submit")
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SubmitModal(self.task_id, self))

    @discord.ui.button(label="Close Task", style=discord.ButtonStyle.red, custom_id="close_task")
    async def close_task_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Load the completed tasks channel ID from config
        with open('vkeeper_config.json', 'r') as config_file:
            config = json.load(config_file)
        completed_channel_id = config['completed_tasks_channel_id']

        # Update task status in the database
        db_manager.update_task_status(self.task_id, "closed")

        # Get the updated task information
        task = db_manager.get_task(self.task_id)

        # Create a new embed for the completed task
        completed_embed = task_embed(task)
        completed_embed.color = discord.Color.red()
        completed_embed.add_field(name="Status", value="Closed", inline=False)

        # Send the completed task to the completed tasks channel
        completed_channel = interaction.guild.get_channel(completed_channel_id)
        await completed_channel.send(embed=completed_embed)

        # Delete the original task message
        try:
            await interaction.message.delete()
        except discord.errors.NotFound:
            # The message was already deleted
            pass

        await interaction.response.send_message("Task marked as closed, moved to the completed tasks channel, and removed from the original channel.", ephemeral=True)


class CustomTaskManagerView(discord.ui.View):
    def __init__(self, task_id):
        super().__init__(timeout=None)
        self.task_id = task_id
        # Add a custom ID to the view
        self.custom_id = f"custom_task_manager_{task_id}"
        
    async def update_message(self, interaction: discord.Interaction):
        updated_task = db_manager.get_custom_task(self.task_id)
        updated_embed = custom_task_embed(updated_task)
        await interaction.response.edit_message(embed=updated_embed, view=self)

    @discord.ui.button(label="Pick task", style=discord.ButtonStyle.green, custom_id="sign_up")
    async def sign_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        task = db_manager.get_custom_task(self.task_id)
        assigned_users = json.loads(task['assigned_users'])
        
        if user_id in assigned_users:
            # User is already assigned, so remove them
            assigned_users.remove(user_id)
            action = "dropped from"
            button.label = "Pick task"
            button.style = discord.ButtonStyle.green
        else:
            # User is not assigned, so add them
            assigned_users.append(user_id)
            action = "signed up for"
            button.label = "Drop Task"
            button.style = discord.ButtonStyle.gray
        
        db_manager.update_custom_task_assigned_users(self.task_id, json.dumps(assigned_users))
        
        # Update the embed with the new user list
        await self.update_message(interaction)
        
        await interaction.followup.send(f"You've been {action} the task!", ephemeral=True)

    @discord.ui.button(label="Submit", style=discord.ButtonStyle.blurple, custom_id="submit")
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SubmitModal(self.task_id))

    @discord.ui.button(label="Close Task", style=discord.ButtonStyle.red, custom_id="close_custom_task")
    async def close_custom_task_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Mark the task as closed in the database
            db_manager.close_custom_task(self.task_id)
            logger.info(f"Task {self.task_id} marked as closed in the database")
            
            # Delete the original message
            await interaction.message.delete()
            logger.info(f"Message for task {self.task_id} deleted")
            
            # Send a confirmation message
            await interaction.response.send_message(f"Task {self.task_id} has been closed and removed.", ephemeral=True)
            
            self.stop()  # This disables the buttons
            logger.info(f"View stopped for task {self.task_id}")
        except Exception as e:
            logger.error(f"Error in close_custom_task_button for task {self.task_id}: {str(e)}")
            await interaction.response.send_message(f"An error occurred while closing the task: {str(e)}", ephemeral=True)

class SubmitModal(discord.ui.Modal, title='Submit Progress'):
    amount = discord.ui.TextInput(label='Amount to submit')

    def __init__(self, task_id, view):
        super().__init__()
        self.task_id = task_id
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount.value)
            task = db_manager.get_task(self.task_id)
            new_amount = task['current_amount'] + amount
            db_manager.update_task_progress(self.task_id, new_amount)
            
            await self.view.update_message(interaction)
            logger.info(f"Embed updated")
            await interaction.followup.send(f"Successfully submitted {amount}.", ephemeral=True)
            
            if new_amount >= task['amount']:
                
                with open('vkeeper_config.json', 'r') as config_file:
                    config = json.load(config_file)
                completed_channel_id = config['completed_tasks_channel_id']

                # Update task status in the database
                db_manager.update_task_status(self.task_id, "closed")

                # Get the updated task information
                task = db_manager.get_task(self.task_id)

                # Create a new embed for the completed task
                completed_embed = task_embed(task)
                completed_embed.color = discord.Color.green()
                completed_embed.add_field(name="Status", value="Completed", inline=False)

        # Send the completed task to the completed tasks channel
                completed_channel = interaction.guild.get_channel(completed_channel_id)
                await completed_channel.send(embed=completed_embed)
                try:
                    await interaction.message.delete()
                except discord.errors.NotFound:
                    # The message was already deleted
                    pass

                await interaction.response.send_message("Task marked as completed, moved to the completed tasks channel, and removed from the original channel.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in SubmitModal: {str(e)}")
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

class RoleSelect(discord.ui.Select):
    def __init__(self, member: discord.Member):
        self.member = member
        # Define the dropdown options
        options = [
            discord.SelectOption(label="Ally", description="Assign the Ally role"),
            discord.SelectOption(label="Seaman", description="Assign the Member role"),
        ]
        
		  # Initialize the dropdown
        super().__init__(placeholder="Choose the role to assign...", min_values=1, max_values=1, options=options)
    
    async def callback(self, interaction: discord.Interaction):
        selected_role = self.values[0]
        role = discord.utils.get(interaction.guild.roles, name=selected_role)
        guild = interaction.guild
        if selected_role == "Ally":
           role = discord.utils.get(guild.roles, name="Ally")
        elif selected_role == "Seaman":
           role = discord.utils.get(guild.roles, name="Seaman")
        verified_role = discord.utils.get(guild.roles, name="Legionnaire")
        
        if role and verified_role:
            await self.member.add_roles(verified_role, role)
            await interaction.response.send_message(f"{self.member.mention} has been verified as a {selected_role}! Welcome to the Republic Coastal Legion! Please be sure to change your server nickname to match your in-game name. Check out <id:browse> for additional optional roles, and take a look at our <id:guide>. Welcome aboard :saluting_face:", ephemeral=False)
        else:
            await interaction.response.send_message("Role not found. Please check role names.", ephemeral=True)

class RoleSelectView(View):
    def __init__(self, member: discord.Member):
        super().__init__()
        self.add_item(RoleSelect(member))

# Define the slash command with the dropdown role selection
@bot.tree.command(name="vouch", description="Verify a new user and assign roles.")
@has_verification_role()
@app_commands.describe(member="The member to verify")
async def vouch(interaction: discord.Interaction, member: discord.Member):
    # Create the dropdown view and send it to the officer
    await interaction.response.send_message("Select the role for the user:", view=RoleSelectView(member), ephemeral=True)

#--Startup
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print(f'Guild ID: {bot.guilds[0].id if bot.guilds else "Not in any guild"}')
    print(f'Bot ID: {bot.user.id}') #Bot ID
    db_manager.connect_db()
    db_manager.create_item_table()
    db_manager.create_facility_table()
    db_manager.create_stockpile_table()
    db_manager.create_tasks_table()
    db_manager.create_custom_tasks_table()
    
    tasks = db_manager.get_all_tasks()
    for task_id, message_id, channel_id in tasks:
        if message_id is None:
            channel = bot.get_channel(channel_id)
            if channel:
                async for message in channel.history(limit=100):
                    if message.author == bot.user and message.embeds:
                        embed = message.embeds[0]
                        if embed.footer.text == f"Task ID: {task_id}":
                            db_manager.update_task_message_id(task_id, message.id)
                            break
        else:
            channel = bot.get_channel(channel_id)
            if channel:
                try:
                    message = await channel.fetch_message(message_id)
                    await message.edit(view=TaskManagerView(task_id))
                except discord.NotFound:
                    print(f"Message {message_id} not found for task {task_id}.")

    bot.add_view(TaskManagerView(None))
    print(f'{bot.user} is ready and tracking task messages.')

@bot.event
async def on_message(message):
	print(f'Message from {message.author}: {message.content}')
	await bot.process_commands(message)
      
@bot.event
async def on_member_join(member):
    # Replace these IDs with your actual channel IDs
    how_to_verify_channel_id = 1293716349578645574
    verification_channel_id = 1293716381358882897
    welcome_channel_id = 1293717909520252938

    # Get the welcome channel using its ID
    channel = bot.get_channel(welcome_channel_id)
    
    if channel:  # Ensure the channel exists
        # Format the welcome message with correct channel mentions using their IDs
        await channel.send(
            f"Welcome {member.mention}! Please follow the instructions in <#{how_to_verify_channel_id}> "
            f"and submit your images in <#{verification_channel_id}>."
        )
#-- Slash Commands --
#Parameters for help slash command can be added in def help()
@bot.tree.command()
async def help(interaction: discord.Interaction):
    """Bot manual"""  # Description when viewing / commands
    help_view = PaginationView(help_manual_data)
    await help_view.send(interaction)

#------ Sync Tree ------
guild = discord.Object(id='1055525730143969350')
# Get Guild ID from right clicking on server icon
# Must have developer mode on discord on setting>Advance>Developer Mode
# More info on tree can be found on discord.py Git Repo
@bot.command()
@commands.guild_only()
@commands.is_owner()
async def sync(
	ctx: Context, guilds: Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
	if not guilds:
		if spec == "~":
			synced = await ctx.bot.tree.sync(guild=ctx.guild)
		elif spec == "*":
			ctx.bot.tree.copy_global_to(guild=ctx.guild)
			synced = await ctx.bot.tree.sync(guild=ctx.guild)
		elif spec == "^":
			ctx.bot.tree.clear_commands(guild=ctx.guild)
			await ctx.bot.tree.sync(guild=ctx.guild)
			synced = []
		else:
			synced = await ctx.bot.tree.sync()
		await ctx.send(
			f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
		)
		return
		
	ret = 0
	for guild in guilds:
		try:
			await ctx.bot.tree.sync(guild=guild)
		except discord.HTTPException:
			pass
		else:
			ret += 1
			
	await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

@bot.tree.command()
@has_command_use_role()
async def add_item(interaction: discord.Interaction, item_name: str, production_facility: str, can_be_crated : str, can_be_palleted : str, crate_size: int, pallet_size : int):
	"""Add item to the database"""
	# Scrape image and other necessary values
	image_url = scraphauler.scrape_image(item_name)
	facilities = db_manager.get_facility_from_db(production_facility)
	
	await interaction.response.send_message("Please enter aliases for item (separate by commas - e.g. \"pcons, pcmats, pcm\"):")
	
	# Wait for user input for aliases
	aliases_msg = await bot.wait_for("message", check=lambda m: m.author == interaction.user)
	item_aliases = aliases_msg.content
	alias_list = item_aliases.split(',')
	formatted_aliases = ",".join([f",{alias.strip()}," for alias in alias_list if alias.strip()])  # Strip spaces
	item_aliases = formatted_aliases
	
	# Store in the database
	db_manager.add_item_to_db(item_name, item_aliases, facilities, can_be_crated, can_be_palleted, 
							crate_size, pallet_size, image_url)

	# Confirm the entry
	await interaction.followup.send(f"Added {item_name} to the database with aliases: {item_aliases}.")
	
@bot.tree.command()
@has_command_use_role()
async def add_facility(interaction: discord.Interaction, facility_name: str):
	"""Add facility to the database"""
	# First response with the initial prompt
	await interaction.response.send_message("Please enter aliases for this facility (separate by commas):")
	
	# Wait for user input for aliases
	facility_aliases_msg = await bot.wait_for("message", check=lambda m: m.author == interaction.user)
	facility_aliases = facility_aliases_msg.content
	alias_list = facility_aliases.split(',')
	formatted_aliases = ",".join([f",{alias.strip()}," for alias in alias_list if alias.strip()])  # Strip spaces
	facility_aliases = formatted_aliases
	
	# Ask for facility type
	await interaction.followup.send("Is this facility World-built or Player-built?")
	
	facility_type_msg = await bot.wait_for("message", check=lambda m: m.author == interaction.user)
	facility_type = facility_type_msg.content

	# Scrape image URL
	image_url = scraphauler.scrape_image(facility_name)
	
	# Add the facility to the database
	db_manager.add_facility_to_db(facility_name, facility_aliases, facility_type, image_url)
	
	# Confirm the addition
	await interaction.followup.send(f"Added {facility_name} to the database with aliases: {facility_aliases}.")

@bot.tree.command()
@has_command_use_role()
async def add_stockpile(interaction: discord.Interaction, stockpile_name : str, stockpile_description : str, stockpile_location : str, stockpile_passcode : int):
	"""Add a stockpile to the database"""
	
	# Store in the database
	db_manager.add_stockpile_to_db(stockpile_name, stockpile_description, stockpile_location, stockpile_passcode)

	# Confirm the entry
	await interaction.response.send_message(f"Added stockpile {stockpile_name} at {stockpile_location} with passcode {stockpile_passcode}. Description: {stockpile_description}.")
	

@bot.tree.command()
@has_command_use_role()
async def create_task(interaction: discord.Interaction, item_name: str, amount: int, facility: str, stockpile: str):
    """Create a new production task"""
    
    # Query the item, facility, and stockpile from the database
    item_info = db_manager.get_item_from_db(item_name)
    facility_info = db_manager.get_facility_from_db(facility)
    stockpile_info = db_manager.get_stockpile_from_db(stockpile)

    # Handle cases where the item, facility, or stockpile aren't found
    if not item_info:
        await interaction.response.send_message(f"Item '{item_name}' not found.")
        return
    if not facility_info:
        await interaction.response.send_message(f"Production facility '{facility}' not found.")
        return
    if not stockpile_info:
        await interaction.response.send_message(f"Stockpile '{stockpile}' not found.")
        return
    
    assigned_users = [str(interaction.user.id)]
    created_by = str(interaction.user.id)
    thumbnail = item_info['image_url']
    
    # Insert the new task into the database
    task_id = db_manager.create_task(item_info['id'], amount, facility_info['id'], stockpile_info['id'], created_by, assigned_users, thumbnail)
    
    if task_id:
        task_data = {
            'id': task_id,
            'item_name': item_info['item_name'],
            'amount': amount,
            'current_amount': 0,
            'facility_name': facility_info['facility_name'],
            'stockpile_name': stockpile_info['stockpile_name'],
            'created_by': created_by,
            'assigned_users': assigned_users,
            'thumbnail': thumbnail,
            'status': 'running'  # Add this line
        }
        task_embed_on_create = task_embed(task_data)
        view = TaskManagerView(task_id)
        
        await interaction.response.send_message(embed=task_embed_on_create, view=view)
        # Save the task message
        message = await interaction.original_response()
        await db_manager.save_task_message(task_id, message.id, interaction.channel_id)
    else:
        await interaction.response.send_message("Failed to create task in the database")

@bot.tree.command()
@has_command_use_role()
async def create_custom_task(interaction: discord.Interaction, task_header: str, task_description: str, task_location: str):
    """Create a new custom task"""
    
    assigned_users = [str(interaction.user.id)]
    created_by = str(interaction.user.id)
    
    # Insert the new task into the database
    task_id = db_manager.create_custom_task(task_header, task_description, task_location, created_by, assigned_users)
    
    if task_id:
        task_embed_on_create = custom_task_embed({
            'id': task_id,
            'task_header': task_header,
            'task_description': task_description,
            'task_location': task_location,
            'created_by': created_by,
            'assigned_users': assigned_users,
        })
        view = CustomTaskManagerView(task_id)
        
        await interaction.response.send_message(embed=task_embed_on_create, view=view)
        # Save the task message
        message = await interaction.original_response()
        await db_manager.save_custom_task_message(task_id, message.id, interaction.channel_id)
    else:
        await interaction.response.send_message("Failed to create task in the database")

@bot.tree.command()
@has_command_use_role()
async def get_item(interaction: discord.Interaction, item_name: str):
	"""Retrieve item information from the database based on the search term."""

	# Connect to the database and search for the facility or its alias
	item_info = db_manager.get_item_from_db(item_name)
	facilities_list = json.loads(item_info['facilities'])
	facility_name = facilities_list['facility_name']

	get_item_embed = discord.Embed(
		colour = discord.Colour.dark_gold(),
		description = "Processing your request, officer...",
		title = "Item Database"
	)
	
	get_item_embed.set_author(name="Velian Keeper Bot")
	
	# Check if facility info was found
	if item_info:
		get_item_embed.add_field(name=":newspaper: Item name", value=item_info['item_name'], inline=True),
		get_item_embed.insert_field_at(1,name=":round_pushpin: Made at", value=facility_name, inline=True),
		get_item_embed.add_field(name="Aliases", value=item_info['item_aliases'], inline=False),
		get_item_embed.add_field(name="Can be crated?", value=item_info['can_be_crated'], inline=True),
		get_item_embed.add_field(name="Can be palletized?", value=item_info['can_be_palleted'], inline=True),
		get_item_embed.add_field(name="\u200b", value="\u200b", inline=True),
		get_item_embed.add_field(name="Crate size", value=item_info['crate_size'], inline=True),
		get_item_embed.add_field(name="Pallet size", value=item_info['pallet_size'], inline=True),
		get_item_embed.add_field(name="\u200b", value="\u200b", inline=True),
		get_item_embed.set_thumbnail(url=item_info['image_url']),
		await interaction.response.send_message(embed=get_item_embed)
	else:
		await interaction.response.send_message(f"No item found for '{item_name}'.")
		
@bot.tree.command()
@has_command_use_role()
async def get_facility(interaction: discord.Interaction, facility_name: str):
	"""Retrieve a facility information."""

	# Connect to the database and search for the facility or its alias
	facility_info = db_manager.get_facility_from_db(facility_name)
	get_facility_embed = discord.Embed(
		colour = discord.Colour.green(),
		description = "Processing your request, officer...",
		title = "Facility Knowledge Database"
	)
	
	get_facility_embed.set_author(name="Velian Keeper Bot")
	
	# Check if facility info was found
	if facility_info:
		get_facility_embed.add_field(name=":newspaper: Facility Name", value=facility_info['facility_name'], inline=True),
		get_facility_embed.insert_field_at(1,name=":round_pushpin: Build type", value=facility_info['facility_type'], inline=True),
		get_facility_embed.add_field(name="Aliases", value=facility_info['facility_aliases'], inline=False),
		get_facility_embed.set_thumbnail(url=facility_info['image_url']),
		await interaction.response.send_message(embed=get_facility_embed)
	else:
		await interaction.response.send_message(f"No facility found for '{facility_name}'.")
		
@bot.tree.command()
@has_command_use_role()
async def get_stockpile(interaction: discord.Interaction, stockpile_name: str):
	"""Review stockpiles info."""

	# Connect to the database and search for the facility or its alias
	stockpile_info = db_manager.get_stockpile_from_db(stockpile_name)
	get_stockpile_embed = discord.Embed(
		colour = discord.Colour.brand_red(),
		description = "This is a restricted facility, i hope you got those papers signed.",
		title = "Stockpile Information"
	)
	
	get_stockpile_embed.set_author(name="Velian Keeper Bot")
	
	# Check if facility info was found
	if stockpile_info:
		get_stockpile_embed.add_field(name=":newspaper: Stockpile Name", value=stockpile_info['stockpile_name'], inline=True),
		get_stockpile_embed.insert_field_at(1,name=":map: Location", value=stockpile_info['stockpile_location'], inline=True),
		get_stockpile_embed.add_field(name="Description:", value=stockpile_info['stockpile_description'], inline=False),
		get_stockpile_embed.add_field(name="Passcode", value=f"||{stockpile_info['stockpile_passcode']}||", inline=False),
		get_stockpile_embed.set_thumbnail(url="https://static.wikia.nocookie.net/foxhole_gamepedia_en/images/7/73/Icon_Blueprint.png/revision/latest?cb=20180416214806")
		await interaction.response.send_message(embed=get_stockpile_embed)
	else:
		await interaction.response.send_message(f"No stockpile found for '{stockpile_name}'.")
	
@bot.tree.command()
@has_critical_command_use_role()
async def purge_all_tasks(interaction: discord.Interaction):
	await interaction.response.send_message("**THIS WILL DELETE ALL CREATED TASKS. THIS ACTION IS IRREVERSIBLE.** Do you want to delete all current tasks? Type YES to proceed")
	purge = await bot.wait_for("message", check=lambda m: m.author == interaction.user)
	
	if purge.content in ['YES']:
		db_manager.purge_tasks()
		await interaction.followup.send("All tasks have been deleted. \n*Now you become death. The destroyer of worlds.*")
	else :
		await interaction.followup.send("No action has been taken. All tasks are running.")
	
@bot.tree.command()
@has_critical_command_use_role()
async def purge_all_stockpiles(interaction: discord.Interaction):
	await interaction.response.send_message("**THIS WILL DELETE ALL KNOWN STOCKPILES. THIS ACTION IS IRREVERSIBLE.** Do you want to delete all current stockpiles? Type YES to proceed")
	purge = await bot.wait_for("message", check=lambda m: m.author == interaction.user)
	
	if purge.content in ['YES']:
		db_manager.purge_stockpiles()
		await interaction.followup.send("All stockpiles have been deleted. \n*Jesus H. Christ, why is your footlocker unlocked?!*")
	else :
		await interaction.followup.send("No action has been taken. All tasks are running.")

class EditItemModalPrimary(discord.ui.Modal, title='Edit Item'):
    def __init__(self, item):
        super().__init__()
        self.item = item
        self.add_item(discord.ui.TextInput(label='Item Name', default=item['item_name']))
        self.add_item(discord.ui.TextInput(label='Aliases', default=item['item_aliases']))
        self.add_item(discord.ui.TextInput(label='Can be crated?', default=str(item['can_be_crated'])))
        self.add_item(discord.ui.TextInput(label='Can be palletized?', default=str(item['can_be_palleted'])))
        self.add_item(discord.ui.TextInput(label='Image URL', default=item['image_url']))

    async def on_submit(self, interaction: discord.Interaction):
        self.item['item_name'] = self.children[0].value
        self.item['item_aliases'] = self.children[1].value
        self.item['can_be_crated'] = self.children[2].value
        self.item['can_be_palleted'] = self.children[3].value
        self.item['image_url'] = self.children[4].value

        success = db_manager.update_item(self.item)
        if success:
            view = EditItemSecondaryView(self.item)
            await interaction.response.send_message(
                "Primary fields updated successfully. Click the button below to edit secondary fields.",
                view=view,
                ephemeral=True
            )
        else:
            await interaction.response.send_message("Failed to update the item. Please try again.", ephemeral=True)

class EditItemSecondaryView(discord.ui.View):
    def __init__(self, item):
        super().__init__()
        self.item = item

    @discord.ui.button(label="Edit Secondary Fields", style=discord.ButtonStyle.primary)
    async def edit_secondary(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditItemModalSecondary(self.item))

class EditItemModalSecondary(discord.ui.Modal, title='Edit Secondary Fields'):
    def __init__(self, item):
        super().__init__()
        self.item = item
        self.add_item(discord.ui.TextInput(label='Crate Size', default=str(item['crate_size'])))
        self.add_item(discord.ui.TextInput(label='Pallet Size', default=str(item['pallet_size'])))
        self.add_item(discord.ui.TextInput(label='Facilities', default=str(item['facilities'])))

    async def on_submit(self, interaction: discord.Interaction):
        self.item['crate_size'] = self.children[0].value
        self.item['pallet_size'] = self.children[1].value
        self.item['facilities'] = self.children[2].value

        success = db_manager.update_item(self.item)
        if success:
            await interaction.response.send_message(f"Item '{self.item['item_name']}' has been fully updated.", ephemeral=True)
        else:
            await interaction.response.send_message("Failed to update secondary fields. Please try again.", ephemeral=True)

@bot.tree.command()
@has_critical_command_use_role()
async def edit_item(interaction: discord.Interaction, item_name: str):
    """Edit an existing item in the database"""
    item = db_manager.get_item_from_db(item_name)
    if not item:
        await interaction.response.send_message(f"Item '{item_name}' not found in the database.", ephemeral=True)
        return
    
    await interaction.response.send_modal(EditItemModalPrimary(item))

@bot.tree.command()
@has_critical_command_use_role()
async def delete_item(interaction: discord.Interaction, item_name: str):
    """Delete an item from the database."""
    
    # Check if the item exists using the database manager
    item_exists = db_manager.get_item_by_name(item_name)

    if item_exists is None:
        await interaction.response.send_message(f"No item found with the name: {item_name}.", ephemeral=True)
        return

    # Confirmation message
    await interaction.response.send_message(f"Are you sure you want to delete the item '{item_name}'? Type 'yes' to confirm.", ephemeral=True)

    # Wait for the user's confirmation
    def check(m):
        return m.author == interaction.user and m.content.lower() == "yes"

    try:
        # Wait for user confirmation
        msg = await bot.wait_for('message', check=check, timeout=30.0)

        # Delete the item using the database manager
        db_manager.delete_item_by_name(item_name)
        
        await interaction.followup.send(f"Item '{item_name}' has been successfully deleted.", ephemeral=True)

    except asyncio.TimeoutError:
        await interaction.followup.send("Timeout: Item deletion canceled.", ephemeral=True)

@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f"An error occurred in event {event}")
    logger.error(f"Args: {args}")
    logger.error(f"Kwargs: {kwargs}")
    logger.error(traceback.format_exc())

bot.run(bot_token)

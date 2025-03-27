import discord
import random
import json
import asyncio
import time
import os
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("TOKEN")
ALLOWED_CHANNEL_ID = 1354769726261428224  # Channel where bot is allowed to run
OWNER_ID = 598460565387476992  # User ID of the person who can give money
steal_cooldowns = {}
work_cooldowns = {}

# Load user balances from a JSON file
def load_balances():
    try:
        with open("balances.json", "r") as f:
            balances = json.load(f)
            return {k: v if isinstance(v, dict) else {"wallet": v, "rebirth": 0} for k, v in balances.items()}  # Ensure all balances are dictionaries
    except FileNotFoundError:
        return {}

def save_balances(balances):
    with open("balances.json", "w") as f:
        json.dump(balances, f, indent=4)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return
    
    if message.channel.id != ALLOWED_CHANNEL_ID and not message.content.startswith(".work"):
        return
    
    balances = load_balances()
    user_id = str(message.author.id)
    
    if user_id not in balances or not isinstance(balances[user_id], dict):
        balances[user_id] = {"wallet": 1000, "rebirth": 0}

    rebirth_threshold = (balances[user_id]["rebirth"] + 1) * 20000 - 10000  # 10k, 30k, 60k, 90k, etc.
    if balances[user_id]["wallet"] >= rebirth_threshold:
        await message.channel.send(f"✨ {message.author.mention}, you have reached {rebirth_threshold} coins! Use `.rebirth` to reset and gain double winnings!")
    
    if message.content.startswith(".balance"):
        wallet = balances[user_id]["wallet"]
        embed = discord.Embed(
            title=f"{message.author.name}'s Balance",
            description=f"💰 Wallet: **{wallet}** coins",
            color=discord.Color.gold()
        )
        await message.channel.send(embed=embed)

    elif message.content.startswith(".gamble"):
        parts = message.content.split()
        if len(parts) != 2 or not parts[1].isdigit():
            await message.channel.send("❌ Usage: .gamble <amount>")
            return
        
        amount = int(parts[1])
        wallet = balances[user_id]["wallet"]
        
        if amount <= 0:
            await message.channel.send("❌ Invalid bet amount!")
            return
        
        if amount > wallet:
            await message.channel.send("❌ You don't have enough coins in your wallet!")
            return
        
        outcome = "win" if random.randint(1, 100) <= 40 else "lose"
        multiplier = 2 ** balances[user_id]["rebirth"]
        
        if outcome == "win":
            winnings = amount * multiplier
            wallet += winnings
            result = f"🎉 You won {winnings} coins!"
            color = discord.Color.green()
        else:
            wallet -= amount
            result = f"💀 You lost {amount} coins!"
            color = discord.Color.red()
        
        balances[user_id]["wallet"] = wallet
        save_balances(balances)
        
        embed = discord.Embed(
            title="🎲 Gambling Result",
            description=result,
            color=color
        )
        embed.add_field(name="New Wallet Balance", value=f"💰 {wallet} coins", inline=False)
        await message.channel.send(embed=embed)
    
    elif message.content.startswith(".rebirth"):
        if balances[user_id]["wallet"] >= rebirth_threshold:
            balances[user_id]["wallet"] = 1000
            balances[user_id]["rebirth"] += 1
            save_balances(balances)
            await message.channel.send(f"🌟 {message.author.mention}, you have rebirthed! Your balance has been reset, but your winnings now increase by 0.10x per rebirth!")
        else:
            await message.channel.send(f"❌ You need at least {rebirth_threshold} coins to rebirth!")
    
    elif message.content.startswith(".leaderboard"):
        sorted_balances = sorted(balances.items(), key=lambda x: x[1]["wallet"], reverse=True)[:10]
        embed = discord.Embed(title="🏆 Leaderboard", description="Top 10 wealthiest users:", color=discord.Color.purple())
        for i, (user_id, data) in enumerate(sorted_balances, start=1):
            user = await client.fetch_user(int(user_id))
            embed.add_field(name=f"#{i} {user.name}", value=f"💰 {data['wallet']} coins", inline=False)
        await message.channel.send(embed=embed)
    
    elif message.content.startswith(".givemoney") and message.author.id == OWNER_ID:
        parts = message.content.split()
        if len(parts) != 2 or not parts[1].isdigit():
            await message.channel.send("❌ Usage: .givemoney <amount>")
            return
        
        amount = int(parts[1])
        for user in balances:
            balances[user]["wallet"] += amount
        save_balances(balances)
        await message.channel.send(f"💰 {amount} coins have been given to everyone by {message.author.mention}!")
    elif message.content.startswith(".reset") and message.author.id == OWNER_ID:
        parts = message.content.split()
        if len(parts) != 2 or not parts[1].isdigit():
            await message.channel.send("❌ Usage: .reset <user_id>")
            return
        
        target_id = parts[1]
        if target_id not in balances:
            await message.channel.send("❌ User not found in balance records!")
            return
        
        balances[target_id]["wallet"] = 1000
        save_balances(balances)
        await message.channel.send(f"🔄 {message.author.mention} has reset <@{target_id}>'s balance to 1000 coins!")

    elif message.content.startswith(".give") and message.author.id == OWNER_ID:
        parts = message.content.split()
        if len(parts) != 3 or not parts[2].isdigit():
            await message.channel.send("❌ Usage: .give @user <amount>")
            return

        target = message.mentions[0] if message.mentions else None
        if not target:
            await message.channel.send("❌ You must mention a user to give money!")
            return

        amount = int(parts[2])
        target_id = str(target.id)

        if target_id not in balances:
            balances[target_id] = {"wallet": 1000, "rebirth": 0}

        balances[target_id]["wallet"] += amount
        save_balances(balances)
        await message.channel.send(f"💰 {message.author.mention} gave {amount} coins to {target.mention}!")
    elif message.content.startswith(".steal"):
        if user_id in steal_cooldowns and time.time() - steal_cooldowns[user_id] < 60:
            await message.channel.send("⏳ You must wait 1 minute before stealing again!")
            return
        
        parts = message.content.split()
        if len(parts) != 3 or not parts[2].isdigit():
            await message.channel.send("❌ Usage: .steal @user <amount>")
            return
        
        target = message.mentions[0] if message.mentions else None
        if not target:
            await message.channel.send("❌ You must mention a user to steal from!")
            return
        
        amount = int(parts[2])
        target_id = str(target.id)
        
        if target_id not in balances or balances[target_id]["wallet"] < amount:
            await message.channel.send("❌ Target does not have enough coins!")
            return
        
        if random.randint(1, 100) <= 2:
            balances[user_id]["wallet"] += amount
            balances[target_id]["wallet"] -= amount
            await message.channel.send(f"💰 {message.author.mention} successfully stole {amount} coins from {target.mention}!")
        else:
            await message.channel.send(f"🚔 {message.author.mention} failed to steal from {target.mention} and got caught!")
        
        steal_cooldowns[user_id] = time.time()
        save_balances(balances)

    elif message.content.startswith(".work"):
        current_time = time.time()
        
        if user_id in work_cooldowns and current_time - work_cooldowns[user_id] < 300:  # 5 minutes (300 sec)
            remaining_time = int(300 - (current_time - work_cooldowns[user_id]))
            minutes, seconds = divmod(remaining_time, 60)
            await message.channel.send(f"⏳ {message.author.mention}, you need to wait {minutes}m {seconds}s before using `.work` again!")
            return
        
        work_cooldowns[user_id] = current_time  # Update cooldown

        questions = []
        operators = ["+", "-", "*", "/"]
        for _ in range(7):
            num1, num2 = random.randint(1, 20), random.randint(1, 20)
            op = random.choice(operators)

            # Ensure division results in an integer
            if op == "/":
                num1 = num2 * random.randint(1, 10)

            question = f"{num1} {op} {num2}"
            answer = round(eval(question), 2)  # Use round to avoid floating point issues
            questions.append((question, answer))

        try:
            dm_channel = await message.author.create_dm()
            await dm_channel.send("📚 You have started work! Answer these 7 math questions correctly to earn coins.")

            correct_answers = 0
            for i, (question, answer) in enumerate(questions):
                await dm_channel.send(f"Question {i+1}: `{question}`")
                try:
                    response = await client.wait_for(
                        "message",
                        timeout=15.0,
                        check=lambda m: m.author == message.author and m.channel == dm_channel
                    )
                    if response.content.strip() == str(answer):
                        correct_answers += 1
                except asyncio.TimeoutError:
                    await dm_channel.send("⏳ Time's up for this question!")

            reward = correct_answers * 100  # 100 coins per correct answer
            balances[user_id]["wallet"] += reward
            save_balances(balances)

            await dm_channel.send(f"✅ You got {correct_answers}/7 correct and earned {reward} coins! 💰")
        except discord.Forbidden:
            await message.channel.send("❌ I couldn't DM you! Please enable direct messages.")
  
    elif message.content.startswith(".help"):
        embed = discord.Embed(
            title="🛠️ Bot Commands",
            description="Here are the available commands:",
            color=discord.Color.blue()
        )
        embed.add_field(name=".balance", value="Check your wallet balance. 💰", inline=False)
        embed.add_field(name=".gamble <amount>", value="Gamble your coins for a chance to win more! 🎲", inline=False)
        embed.add_field(name=".rebirth", value="Rebirth to reset your balance but increase winnings! 🌟", inline=False)
        embed.add_field(name=".leaderboard", value="View the top 10 wealthiest users. 🏆", inline=False)
        embed.add_field(name=".givemoney <amount>", value="[Owner Only] Give money to all users. 💸", inline=False)
        embed.add_field(name=".reset <user_id>", value="[Owner Only] Reset a user's balance. 🔄", inline=False)
        embed.add_field(name=".give @user <amount>", value="[Owner Only] Give money to a specific user. 🎁", inline=False)
        embed.add_field(name=".steal @user <amount>", value="Attempt to steal coins from another user. 🚔", inline=False)
        embed.add_field(name=".work", value="Answer math questions to earn money! 📚", inline=False)
        await message.channel.send(embed=embed)

client.run(TOKEN)

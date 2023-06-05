import discord

class MyModal(discord.ui.Modal, title='Questionnaire Response'):
    name = discord.ui.TextInput(label='What is your RSN?')
    account_type = discord.ui.TextInput(label='Account Type (Main/Ironman/Etc.)')
    activities = discord.ui.TextInput(label='Activities most interested in')
    timezone = discord.ui.TextInput(label='Timezone')
    clans = discord.ui.TextInput(label='Have you been in any other clans? Why did you leave?')
    referrals = discord.ui.TextInput(label='How did you hear about RS Boomers?')
    wise_old = discord.ui.TextInput(label='Have you enabled Wise Old Man in Runelite?')
    additionaL_info = discord.ui.TextInput(label="Any addition information:", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title='New Application', description=self.name.value, color=0x00FFFF)
        embed.add_field(name=self.account_type.label, value=self.account_type.value, inline=True)
        embed.add_field(name=self.activities.label, value=self.activities.value, inline=False)
        embed.add_field(name=self.additionaL_info.label, value=self.additionaL_info.value, inline=False)
        await interaction.response.send_message(embed=embed)
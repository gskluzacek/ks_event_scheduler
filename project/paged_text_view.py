import discord

from discord_paginator import PageInfo


class PagedTextView(discord.ui.View):
    """ Interactive pagination controls for Discord messages.

    Only the user who created the view can interact with it.
    Example:
        view = PagedTextView(owner_id=interaction.user.id, pages=pages)
        await interaction.response.send_message(pages[0].content, view=view, ephemeral=True)
    """
    def __init__(self, owner_id: int, pages: list[PageInfo], *, timeout: float = 300.0) -> None:
        super().__init__(timeout=timeout)
        if not pages:
            raise ValueError("PagedTextView requires at least one page")
        self.owner_id = owner_id
        self.pages = pages
        self.current_page = 0
        # added per chat gpt to disable button when timeout elapses
        self.message: discord.Message | None = None

        # removed per chat GPT - trying to fix issue
        # self._update_button_state()

    def setup(self) -> None:
        """ Initialize button state after View construction."""
        self._update_button_state()

    # added per chat gpt to disable button when timeout elapses
    def set_message(self, message: discord.Message) -> None:
        """ Store the Discord message controlled by this View.

        Needed so on_timeout() can edit the message after the interaction that created it no longer exists.
        """
        self.message = message

    # commenting out old version per chat GPT - trying to fix issue
    # def _update_button_state(self) -> None:
    #     """ Enable/disable buttons based on current page. """
    #
    #     self.previous_button.disabled = (self.current_page == 0)
    #     self.next_button.disabled = (self.current_page >= len(self.pages) - 1)

    # new function version per chat GPT - trying to fix issue
    def _update_button_state(self) -> None:
        """ Enable/disable buttons based on current page. """
        for item in self.children:
            if not isinstance(item, discord.ui.Button):
                continue
            if item.label == "◀ Previous":
                item.disabled = self.current_page == 0
            elif item.label == "Next ▶":
                item.disabled = (self.current_page >= len(self.pages) - 1)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Called before any button callback.

        Prevents other users from changing the page.
        """
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Only the user who requested this list can navigate pages.",
                ephemeral=True,
            )
            return False

        return True

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary)
    async def previous_button(self: "PagedTextView", interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        """Move to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
        self._update_button_state()
        await interaction.response.edit_message(content=self.pages[self.current_page].content, view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_button(self: "PagedTextView", interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        """Move to next page."""
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
        self._update_button_state()
        await interaction.response.edit_message(content=self.pages[self.current_page].content, view=self)

    # commented out old version per chat gpt to disable button when timeout elapses
    # async def on_timeout(self) -> None:
    #     """ Disable buttons after timeout.
    #
    #     This prevents stale buttons from appearing usable.
    #     """
    #     for item in self.children:
    #         if isinstance(item, discord.ui.Button):
    #             item.disabled = True
    #
    #     # The message is not automatically edited by Discord.
    #     #
    #     # We cannot call edit_message here because the timeout event
    #     # does not provide the interaction that created the message.
    #     #
    #     # Discord will simply reject button clicks after timeout.

    # added new verion per chat gpt to disable button when timeout elapses
    async def on_timeout(self) -> None:
        """ Disable buttons after timeout and update the Discord message. """

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        if self.message is not None:
            await self.message.edit(view=self)

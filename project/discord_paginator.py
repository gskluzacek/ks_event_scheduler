"""
Discord pagination utilities.

Provides:
    - PagedTextBuilder:
        Builds Discord-safe pages from arbitrary text blocks.

    - PagedTextView:
        Interactive Discord UI view with Previous/Next buttons.

The paginator is designed for slash commands where the output can exceed
Discord's 2,000 character message limit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


# Discord maximum message length is 2000 characters.
# We reserve some room for the title and page indicator.
DEFAULT_MAX_MESSAGE_LENGTH = 1900


@dataclass
class PageInfo:
    """ Represents a single generated page. """
    page_number: int
    total_pages: int
    content: str


class PagedTextBuilder:
    """ Builds Discord-safe pages.

    Each item added to the builder is treated as an atomic block.
    The builder will never split an individual item across pages.
    Example:
        builder = PagedTextBuilder( title="Account List" )
        for account in accounts:
            builder.add_item(format_account(account))
        pages = builder.build()
    """
    def __init__(
            self,
            title: str,
            *,
            max_message_length: int = DEFAULT_MAX_MESSAGE_LENGTH,
            codeblock_language: str | None = "text",
    ) -> None:
        self.title = title
        self.max_message_length = max_message_length
        self.codeblock_language = codeblock_language
        self._items: list[str] = []

    def add_item(self, text: str) -> None:
        """ Add one atomic block.

        A block will never be split between pages.
        """
        if not text:
            return
        self._items.append(text)

    def add_items(self, items: Iterable[str]) -> None:
        """ Add multiple blocks. """
        for item in items:
            self.add_item(item)

    def _format_page_header(self, page_number: int, total_pages: int) -> str:
        """ Creates the page header.

        Example:
            ✅ Account List
            Page 1/5
        """
        return f"✅ {self.title}\nPage {page_number}/{total_pages}\n"

    def _wrap_codeblock(self, content: str) -> str:
        """ Wrap page contents in a Discord code block. """
        if self.codeblock_language:
            return f"```{self.codeblock_language}\n{content}\n```"
        return f"```\n{content}\n```"

    def _calculate_page_length(self, content: str, page_number: int, total_pages: int) -> int:
        """ Calculates final Discord message length. """
        return len(
            self._format_page_header(page_number, total_pages) +
            self._wrap_codeblock(content)
        )

    def _split_into_pages(self) -> list[str]:
        """ Splits items into raw pages.

        This happens before the page numbers are known.
        """
        pages: list[str] = []
        current_page: list[str] = []
        current_length = 0

        # Account for:
        #
        # title
        # page indicator
        # code block markers
        #
        # We intentionally leave extra room because
        # Page 999/999 is longer than Page 1/2.

        overhead = 100

        for item in self._items:
            item_length = len(item) + 1

            if current_page:
                would_be_length = current_length + item_length + overhead
            else:
                would_be_length = item_length + overhead

            if would_be_length > self.max_message_length and current_page:
                pages.append("\n".join(current_page))
                current_page = []
                current_length = 0

            current_page.append(item)
            current_length += item_length

        if current_page:
            pages.append("\n".join(current_page))

        return pages

    def build(self) -> list[PageInfo]:
        """ Build final pages.

        Returns:
            list[PageInfo]
        """
        raw_pages = self._split_into_pages()
        if not raw_pages:
            return []
        total_pages = len(raw_pages)
        result: list[PageInfo] = []

        for index, content in enumerate(raw_pages, start=1):
            page = PageInfo(
                page_number=index,
                total_pages=total_pages,
                content=(
                    self._format_page_header(index, total_pages) +
                    self._wrap_codeblock(content)
                ),
            )

            # Safety check.
            #
            # This should never fail because the builder reserves space,
            # but keeping the check here protects against future changes.
            if len(page.content) > 2000:
                raise ValueError(
                    f"Generated Discord page exceeds 2000 characters: "
                    f"{len(page.content)}"
                )
            result.append(page)

        return result

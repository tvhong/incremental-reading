# Copyright 2013 Tiago Barroso
# Copyright 2013 Frank Kmiec
# Copyright 2013-2016 Aleksej
# Copyright 2017 Christian Weiß
# Copyright 2018 Timothée Chauvin
# Copyright 2017-2019 Joseph Lorimer <joseph@lorimer.me>
#
# Permission to use, copy, modify, and distribute this software for any purpose
# with or without fee is hereby granted, provided that the above copyright
# notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

from re import sub
from typing import Sequence

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from anki.decks import DeckId
from anki.cards import Card, CardId
from anki.utils import strip_html
from aqt import mw
from aqt.utils import showInfo

from .settings import SettingsManager
from .util import showBrowser

SCHEDULE_EXTRACT = 0
SCHEDULE_SOON = 1
SCHEDULE_LATER = 2
SCHEDULE_CUSTOM = 3


class PriorityQueueScheduler:
    _deckId = None
    _cardListWidget = None
    _settings: SettingsManager = None

    def changeProfile(self, settings: SettingsManager):
        self._settings = settings

    def showDialog(self, currentCard: Card = None):
        if currentCard:
            self._deckId = currentCard.did
        elif mw._selectedDeck():
            self._deckId = mw._selectedDeck()['id']
        else:
            return

        if not self._getCardInfo(self._deckId):
            showInfo('Please select an Incremental Reading deck.')
            return

        dialog = QDialog(mw)
        layout = QVBoxLayout()
        self._cardListWidget = QListWidget()
        self._cardListWidget.setAlternatingRowColors(True)
        self._cardListWidget.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self._cardListWidget.setWordWrap(True)
        self._cardListWidget.itemDoubleClicked.connect(
            lambda: showBrowser(
                self._cardListWidget.currentItem().data(Qt.ItemDataRole.UserRole)['nid']
            )
        )

        self._updateListItems()

        buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        buttonBox.rejected.connect(dialog.reject)
        buttonBox.setOrientation(Qt.Orientation.Horizontal)

        layout.addWidget(self._cardListWidget)
        layout.addWidget(buttonBox)

        dialog.setLayout(layout)
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.resize(500, 500)
        dialog.exec()

    def _updateListItems(self):
        cardInfo = self._getCardInfo(self._deckId)
        self._cardListWidget.clear()
        posWidth = len(str(len(cardInfo) + 1))
        for i, card in enumerate(cardInfo, start=1):
            info = str(i).zfill(posWidth)
            title = sub(r'\s+', ' ', strip_html(card['title']))
            text = self._settings['organizerFormat'].format(
                info=info, title=title
            )
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, card)
            self._cardListWidget.addItem(item)

    def _getSelected(self):
        return [
            self._cardListWidget.item(i)
            for i in range(self._cardListWidget.count())
            if self._cardListWidget.item(i).isSelected()
        ]

    def answer(self, card: Card, ease: int):
        # TODO: after answer, set new due date based on card's priority and current interval
        pass

    def _getCardInfo(self, deckId: DeckId):
        # TODO: get the list of items overdue
        deck = mw.col.decks.get(deckId)
        cardIds = mw.col.find_cards(f'deck:"{deck.get("name")}"')
        cards = (mw.col.get_card(cid) for cid in cardIds)
        irCards = (c for c in cards if c.note_type()['name'] == self._settings['modelName'])
        irCardsInfo = (
            {
                'id': c.id,
                'nid': c.note().id,
                'title': c.note()[self._settings['titleField']],
                'priority': c.note()[self._settings['prioField']] if self._settings['prioEnabled'] else None
            }
            for c in irCards
        )

        return list(irCardsInfo)

"""
Utility functions and classes for the Fake Hockey Bot
Copyright (C) 2022 NotAName

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from typing import Literal, Optional


def fancy_archetype_name(position: str, archetype: str) -> Optional[str]:
    """
    If given a non-goalie position and a string 'passer', 'shooter', or 'deker' (case insensitive), returns a string corresponding
    to proper name per rulebook. Returns None otherwise.
    """
    position, archetype = position.upper(), archetype.upper()
    if position == "FORWARD":
        return {"PASSER": "Playmaker", "SHOOTER": "Sniper", "DEKER": "Dangler"}[archetype]
    if position == "DEFENSEMAN":
        return {"PASSER": "Enforcer", "SHOOTER": "Offensive Defenseman", "DEKER": "Finesser"}[archetype]
    return None


def home_away_opposite(home_away: str) -> Optional[Literal["HOME", "AWAY"]]:
    """
    If given the str value "HOME" or "AWAY" (case insensitive), returns the opposite in all caps. Returns None otherwise.
    """
    home_away = home_away.upper()
    if home_away == "HOME":
        return "AWAY"
    elif home_away == "AWAY":
        return "HOME"
    return None

import json
from typing import Dict, Any, List
import xml.etree.ElementTree as ET


def _get_text(elem: ET.Element, xpath: str) -> str:
    node = elem.find(xpath)
    return node.get("value") if node is not None and "value" in node.attrib else ""


def _get_int(elem: ET.Element, xpath: str) -> int:
    text = _get_text(elem, xpath)
    try:
        return int(text)
    except (TypeError, ValueError):
        return 0


def _get_float(elem: ET.Element, xpath: str) -> float:
    text = _get_text(elem, xpath)
    try:
        return float(text)
    except (TypeError, ValueError):
        return 0.0


def parse_game_item(item: ET.Element) -> Dict[str, Any]:
    """Parse a <item> node from BGG /thing into structured dicts."""

    game_id = int(item.attrib["id"])

    name = ""
    for name_node in item.findall("name"):
        if name_node.attrib.get("type") == "primary":
            name = name_node.attrib.get("value", "")
            break

    description = (item.findtext("description") or "").strip()

    year_published = _get_int(item, "yearpublished")
    min_players = _get_int(item, "minplayers")
    max_players = _get_int(item, "maxplayers")
    playing_time = _get_int(item, "playingtime")
    min_playtime = _get_int(item, "minplaytime")
    max_playtime = _get_int(item, "maxplaytime")
    min_age = _get_int(item, "minage")

    thumbnail = item.findtext("thumbnail") or ""
    image = item.findtext("image") or ""

    ratings = item.find("statistics/ratings")
    average_rating = bayes_rating = avg_weight = 0.0
    num_ratings = num_comments = 0
    ranks_json = {}

    if ratings is not None:
        def get_rating(name: str, cast=float, default=0):
            node = ratings.find(name)
            if node is None or "value" not in node.attrib:
                return default
            try:
                return cast(node.attrib["value"])
            except (TypeError, ValueError):
                return default

        average_rating = get_rating("average")
        bayes_rating = get_rating("bayesaverage")
        avg_weight = get_rating("averageweight")
        num_ratings = get_rating("usersrated", int, 0)
        num_comments = get_rating("numcomments", int, 0)

        ranks_node = ratings.find("ranks")
        if ranks_node is not None:
            ranks_json["ranks"] = []
            for rank in ranks_node.findall("rank"):
                ranks_json["ranks"].append({
                    "id": rank.attrib.get("id"),
                    "name": rank.attrib.get("name"),
                    "friendlyname": rank.attrib.get("friendlyname"),
                    "value": rank.attrib.get("value"),
                    "bayesaverage": rank.attrib.get("bayesaverage"),
                })

    polls_json = {}
    for poll in item.findall("poll"):
        poll_name = poll.attrib.get("name")
        poll_entry = {
            "title": poll.attrib.get("title"),
            "totalvotes": int(poll.attrib.get("totalvotes", "0") or 0),
        }

        if poll_name == "suggested_numplayers":
            results = []
            for res in poll.findall("results"):
                numplayers = res.attrib.get("numplayers")
                votes = {}
                for opt in res.findall("result"):
                    votes[opt.attrib.get("value")] = int(opt.attrib.get("numvotes", "0") or 0)
                results.append({"numplayers": numplayers, "votes": votes})
            poll_entry["results"] = results

        elif poll_name == "suggested_playerage":
            results = []
            for res in poll.findall("results/result"):
                results.append({
                    "age": res.attrib.get("value"),
                    "numvotes": int(res.attrib.get("numvotes", "0") or 0),
                })
            poll_entry["results"] = results

        elif poll_name == "language_dependence":
            results = []
            for res in poll.findall("results/result"):
                results.append({
                    "level": res.attrib.get("level"),
                    "value": res.attrib.get("value"),
                    "numvotes": int(res.attrib.get("numvotes", "0") or 0),
                })
            poll_entry["results"] = results

        if poll_name:
            polls_json[poll_name] = poll_entry

    links_by_type = {}
    for link in item.findall("link"):
        link_type = link.attrib.get("type")
        if not link_type:
            continue
        links_by_type.setdefault(link_type, []).append({
            "id": int(link.attrib.get("id")),
            "name": link.attrib.get("value", ""),
        })

    game_row = {
        "id": game_id,
        "name": name,
        "description": description,
        "year_published": year_published,
        "min_players": min_players,
        "max_players": max_players,
        "playing_time": playing_time,
        "min_playtime": min_playtime,
        "max_playtime": max_playtime,
        "min_age": min_age,
        "thumbnail": thumbnail,
        "image": image,
        "average_rating": average_rating,
        "bayes_rating": bayes_rating,
        "avg_weight": avg_weight,
        "num_ratings": num_ratings,
        "num_comments": num_comments,
        "ranks_json": json.dumps(ranks_json) if ranks_json else None,
        "polls_json": json.dumps(polls_json) if polls_json else None,
    }

    return {
        "game": game_row,
        "links": links_by_type,
        "polls": polls_json,
        "ranks": ranks_json,
    }

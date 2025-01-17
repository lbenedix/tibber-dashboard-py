import math
import os
import argparse
from datetime import datetime, timezone, timedelta
from lxml import etree
import jinja2
import requests


def fetch_tibber_data(access_token):
    TIBBER_API_URL = "https://api.tibber.com/v1-beta/gql"

    query = """
    {
      viewer {
        homes {
          currentSubscription {
            priceInfo {
              current {
                total
                level
              }
              today {
                total
                startsAt
              }
              tomorrow{
                total
                startsAt
              }
            }
          }
        }
      }
    }
    """

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    response = requests.post(TIBBER_API_URL, json={"query": query}, headers=headers)

    if not response.ok:
        response.raise_for_status()

    data = response.json()
    home = data["data"]["viewer"]["homes"][0]
    prices = [{"x": price["startsAt"], "y": price["total"]} for price in home["currentSubscription"]["priceInfo"]["today"]]

    return {
        "prices": prices,
        "currentPrice": home["currentSubscription"]["priceInfo"]["current"]["total"],
        "currentLevel": home["currentSubscription"]["priceInfo"]["current"]["level"].lower(),
    }


def render_svg(data, price_level, width=300, height=300, scale=1, theme="light"):
    templateLoader = jinja2.FileSystemLoader(searchpath="./")
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template('template.svg.jinja2')

    max_y = max(p['y'] * 100 for p in data)
    step = math.ceil(max_y / 4)
    price_labels = [f"{i * step}" for i in range(5)][1:]

    max_y = max(p['y'] * scale for p in data)
    points = " ".join(f"{(i * width) / (len(data) - 1)},{height - ((p['y'] * scale) / max_y) * height}" for i, p in enumerate(data))

    now = datetime.now(tz=timezone(timedelta(hours=1)))  # Berlin is UTC+1
    current_x = (now.hour - 1 + now.minute / 60) * 12.5 + 135

    svg_content = template.render(
        theme=theme,
        points=points,
        price_labels=price_labels,
        currentX=current_x,
        price_level=price_level,
    )

    return svg_content

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate SVG from Tibber data")
    parser.add_argument("--theme",
                        choices=["light", "dark"],
                        default="dark",
                        help="Theme of the SVG (light or dark)")

    parser.add_argument("--access-token",
                        help="Tibber access token (fallback to TIBBER_TOKEN environment variable if not provided)")

    args = parser.parse_args()

    d = fetch_tibber_data(args.access_token or os.getenv("TIBBER_TOKEN"))

    svg = render_svg(d['prices'], d['currentLevel'], theme=args.theme)

    clean_svg = etree.XML(svg, parser=etree.XMLParser(remove_blank_text=True))

    # with open('output.svg', 'w') as f:
    #     f.write(etree.tostring(clean_svg, pretty_print=True).decode())

    print(etree.tostring(clean_svg).decode())
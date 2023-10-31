
import os
import sys
import json
import requests
import bs4

def parseLevelUps(t):
    rows = t('tr')
    # May have an Event banner as the first row, but normally 10 rows + 1 header
    firstRow = 2 if len(rows) == 12 else 1

    parsed = []
    for rowIdx in range(firstRow, len(rows)):
        r = rows[rowIdx]
        cols = r('td')

        # Level
        level = cols[0].get_text(strip=True)
        if level == 'Welcome':
            level = 1
        else:
            level = int(level[5:])

        # Tokens (Mickey has no cost so has a colspan=4)
        colspan = int(cols[1].attrs.get('colspan', 1))
        if colspan == 1:
            coloffset = 0
            requirements = []

            # Common, Item, Ears, Currency
            for col in range(1, 4):
                link = cols[col].find('a')
                if link:
                    requirements.append({
                        'id': link.attrs['title'].replace(' ', '_'),
                        'cnt': int(link.next_sibling.strip().replace(',', '')),
                    })
        else:
            coloffset = 3
            requirements = []

        # Time
        time = cols[5-coloffset].next_element.strip()
        if time == 'Instant':
            time = 0
        else:
            timeUnits = time[-1:]
            if timeUnits == 's':
                timeMult = 1
            elif timeUnits == 'm':
                timeMult = 60
            elif timeUnits == 'h':
                timeMult = 3600
            time = int(time[:-1]) * timeMult

        # Rewards (not impl)
        #print(f'{level} = {commonCnt}x{commonKey} {itemCnt}x{itemKey} {earsCnt}x{earsKey} {currencyCnt}x{currencyKey} in {time} ')

        o = {
            'level': level,
            'time': time,
            'requirements': requirements,
        }
        parsed.append(o)

    return parsed

def linksTitlesToList(elem):
    # Find all the 'a' elements under elem and return
    # their titles, or None if no a child elements exist
    if elem is None:
        return None
    ret = []
    elemsA = elem('a')
    for elemA in elemsA:
        key = elemA.attrs['title'].replace(' ', '_')
        ret.append(key)

    return ret if len(ret) > 0 else None

def parseActivities(t):
    rows = t('tr')
    parsed = []
    # First row is thead
    for rowIdx in range(1, len(rows)):
        r = rows[rowIdx]
        cols = r('td')
        # Level
        level = int(cols[0].get_text(strip=True))

        # Target + Requires
        # target = cols[1].get_text(strip=True)
        # # Target is usually target[*requires&requires&...]
        # requires = target.split('*')
        # target = requires[0]
        # if len(requires) > 1:
        #     requires = [s.strip() for s in requires[1].split('&')]
        # else:
        #     requires = None

        # find the index of the first bare text item,
        # The first could be the image for "has animation"
        targetIdx = next((i for i, v in enumerate(cols[1].contents) if type(v) == bs4.element.NavigableString), -1)
        target = cols[1].contents[targetIdx].strip()

        small = cols[1].find('small', recursive=False)
        requires = linksTitlesToList(small)

        # + (Wish/Companion)
        plus = cols[2].find('a')
        if plus:
            companion = plus.attrs['title'].replace(' ', '_')
            isWish = companion == 'Wish_Granter'
            if isWish:
                companion = None
            else:
                clvl = cols[2].find('small').get_text(strip=True)
                companion = {
                    'id': companion,
                    'level': int(clvl[4:]),
                }
        else:
            companion = None
            isWish = False

        # Time
        time = cols[3].next_element.strip()
        timeUnits = time[-1:]
        if timeUnits == 's':
            timeMult = 1
        elif timeUnits == 'm':
            timeMult = 60
        elif timeUnits == 'h':
            timeMult = 3600
        time = int(time[:-1]) * timeMult

        # Rewards (notimpl)

        # Tokens
        tokens = linksTitlesToList(cols[5]) or []

        # Result
        o = {
            'level': level,
            'target': target,
            'isWish': isWish,
            'time': time,
            'tokens': tokens,
        }
        if companion:
            o['companion'] = companion
        if requires:
            o['requires'] = requires

        #print(json.dumps(o))
        parsed.append(o)

    return parsed

def parseActor(local_id, remote_id, r):
    print(f'Parsing actor')
    soup = bs4.BeautifulSoup(r, 'html.parser')
    tables = soup('table', class_='article-table')
    # LevelUps, Activities, EventActivities, [LevelUps Release Event]
    if not len(tables) in [3, 4]:
        raise Exception(f'Character tables != 3,4 ({len(tables)})')

    print(f'Parsing levelups')
    levelups = parseLevelUps(tables[0])
    print(f'Parsing activities')
    activities = parseActivities(tables[1])

    return {
        'id': local_id,
        'remote_id': remote_id,
        'name': soup.head.title.next_element.split('|')[0].strip(),
        'version': 0,
        'levelups': levelups,
        'activities': activities,
    }

def downloadActor(remote_id):
    print(f'Downloaing page {remote_id}')
    r = requests.get(f'https://dmk.fandom.com/wiki/{remote_id}', allow_redirects=True)
    if r.status_code != 200:
        raise Exception(f'Could not download page ({r.status_code})')
    return r.content

def scrapeActor(local_id, remote_id=None, forceRefresh=False):
    if remote_id is None:
        remote_id = local_id

    dir = os.path.join('actors', local_id)
    actor_html = os.path.join(dir, 'actor.html')
    if not forceRefresh and os.path.exists(actor_html):
        with open(actor_html, 'rb') as f:
            r = f.read()
    else:
        r = downloadActor(remote_id)
        with open(actor_html, 'wb') as f:
            f.write(r)

    actorobj = parseActor(local_id, remote_id, r)
    with open(os.path.join(dir, 'actor.json'), 'w') as f:
        json.dump(actorobj, f, indent=2)

if __name__ == '__main__':
    local_id = sys.argv[1]
    remote_id = sys.argv[2] if len(sys.argv) > 2 else None

    scrapeActor(local_id, remote_id)


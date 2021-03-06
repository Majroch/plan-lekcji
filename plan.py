#!/usr/bin/env python3
import asyncio, datetime, sys, random
import argparse

from vulcan import Keystore, Account, VulcanHebe
from rich import print
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from setup import setup

MY_GROUP = 'Grupa 2'

parser = argparse.ArgumentParser(description='Displays lesson plan from Vulcan e-school system')
day_group = parser.add_mutually_exclusive_group()
day_group.add_argument('-w', '--week', help='display a weekly timetable', action='store_true')
day_group.add_argument('-d', '--date', help='ISO8901 formatted date')

group = parser.add_mutually_exclusive_group()
group.add_argument('-g', '--group', help=f'set group (default: `{MY_GROUP}`)')
group.add_argument('-b', '--both', help='display both groups', action='store_true')

args = parser.parse_args()
# print(args)

# Week/one day
if args.week:
    target_date = 'week'
elif args.date:
    try:
        target_date = datetime.date.fromisoformat(args.date)
    except:
        target_date = datetime.datetime.now()
else:
    target_date = datetime.datetime.now()

# Group/no group/set group
if args.group:
    MY_GROUP = args.group
elif args.both:
    MY_GROUP = None


grades = []
lessons = []
attendance = []

async def main(target_date):
    global grades
    global lessons
    global attendance

    client = await setup()

    grades = await client.data.get_grades(date_from=target_date)
    tmp = []

    # print(grades)
    # print(type(grades))

    async for grade in grades:
        tmp.append(grade)

    grades = tmp
    # print(grades)

    lessons = await client.data.get_lessons(date_from=target_date)
    tmp = []
    async for lesson in lessons:
        tmp.append(lesson)

    lessons = tmp

    attendance = await client.data.get_attendance(date_from=target_date)
    tmp = []
    async for att in attendance:
        tmp.append(att)

    attendance = tmp
    
    await client.close()

if __name__ == "__main__":
    # For whole week
    if target_date == 'week':
        # Get week start date
        dt = datetime.datetime.now()
        start = dt - datetime.timedelta(days=dt.weekday())

        week_info = {}
        for d in range(5):
            target_date = start + datetime.timedelta(days=d)
            loop = asyncio.get_event_loop()
            loop.run_until_complete(main(target_date))

            week_info[d] = {}
            for lesson in lessons:
                week_info[d][lesson.time.position] = {'lesson': lesson}

            for att in attendance:
                week_info[d][att.time.position]['attendance'] = att

        #  print(week_info)

        # table static
        console = Console()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Lp.", justify="right")
        table.add_column("Poniedziałek")
        table.add_column("Wtorek")
        table.add_column("Środa")
        table.add_column("Czwartek")
        table.add_column("Piątek")

        # Transform it from `day: data` to `1_hour: data` so it can be displayed
        for hour in range(1,9):
            row = [str(hour)]
            for day in range(5):
                cell = week_info[day].get(hour, None)
                # print(cell)
                if cell:
                    lesson = cell['lesson']

                    if lesson.subject:
                        lesson_name = lesson.subject.name

                        name = lesson.subject.name
                        if len(name) > 16:
                            out = lesson.subject.code
                        else:
                            out = lesson.subject.name
                    elif lesson.event:
                        out = '[dark_orange]' + lesson.event + '[/ dark_orange]'
                    else:
                        out = 'NO_INFO'

                    att = cell.get('attendance', None)
                    if att:
                        if att.presence_type:
                            symbol = att.presence_type.symbol
                            if symbol == "▬":
                                symbol = "[red]" + symbol + "[/red]"
                            elif symbol == "●":
                                symbol = "[green]" + symbol + "[/green]"
                            elif symbol == "s":
                                symbol = "[yellow]" + symbol + "[/yellow]"
                        else:
                            symbol = "[dim]b[/dim]"
                    else:
                        symbol = "[dim]b[/dim]"  # repetition is good for learning, right?


                    # Append group name, if MY_GROUP not specified
                    if lesson.group and not MY_GROUP:
                        out = out + ' [dim](' + lesson.group.name + ')[/dim]'
                        
                    out = symbol + ' ' + out
                else:
                    out = ''

                row.append(out)
            
            # print(row)
            table.add_row(*row)

        console.print(table)
    else:
        # For one day only
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main(target_date))
        
        console = Console()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Lp.", justify="right")
        table.add_column("Od")
        table.add_column("Do")
        table.add_column("Przedmiot")
        table.add_column("Obecność", justify="center")

        all_info = {}

        for lesson in lessons:
            if lesson.visible:
                all_info[lesson.time.position] = [lesson]
        for att in attendance:
            if att.time.position in all_info.keys():
                all_info[att.time.position].append(att)

        godziny_nieobecne = []
        for key in sorted(all_info):
            try:
                symbol = all_info[key][1].presence_type.symbol
                if symbol == "▬":
                    symbol = "[red]" + symbol + "[/red]"
                    godziny_nieobecne.append(str(all_info[key][1].time.position))
                elif symbol == "●":
                    symbol = "[green]" + symbol + "[/green]"
                elif symbol == "s":
                    symbol = "[yellow]" + symbol + "[/yellow]"
            except:
                symbol = "[dim]N/A[/dim]"

            lesson = all_info[key][0]

            if lesson.subject:
                name = lesson.subject.name

                name = lesson.subject.name
                if len(name) > 16:
                    name = lesson.subject.code
                else:
                    name = lesson.subject.name
            elif lesson.event:
                name = '[dark_orange]' + lesson.event + '[/ dark_orange]'
            else:
                name = 'NO_INFO'

            if not MY_GROUP:
                if all_info[key][0].group:
                    name = name + ' [dim](' + all_info[key][0].group.name + ')[/dim]'
                
            table.add_row("[green]" + str(all_info[key][0].time.position) + "[/green]", all_info[key][0].time.displayed_time.split("-")[0], all_info[key][0].time.displayed_time.split("-")[1], name, symbol)

        console.print(table)

        if len(godziny_nieobecne) > 0:
            # Generate excuse
            text = None
            if len(godziny_nieobecne) == 1:
                text = f'Proszę o usprawiedliwienie {godziny_nieobecne[0]} godziny lekcyjnej'
            elif len(godziny_nieobecne) > 1:
                text = 'Proszę o usprawiedliwienie godzin: ' + ', '.join(godziny_nieobecne)
            
            text += " z dnia " + str(target_date.strftime("%d.%m.%Y"))
        
            excuses = [' z powodu problemów z internetem.', ' z powodów rodzinnych.', '. Musiałem załatwić sprawę w urzędzie.', ', ponieważ miałem problemy z komputerem (Aktualizacja Windows\'a).', ', musiałem opiekować się bratem.']
            if len(godziny_nieobecne) > 1:
                excuses.append(", ponieważ byłem u lekarza")
            if text:
                text += random.choice(excuses)
                print(Panel(text, expand=False))

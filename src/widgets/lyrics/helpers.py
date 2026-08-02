# helpers.py

def prepare_lrc(lrc_str:str) -> list:
    lrc_lines = []
    for line in lrc_str.split('\n'):
        if line.startswith('['):
            timestamp, content = line[1:].split(']')[:2]
            minutes_str, rest = timestamp.split(':')[:2]
            diveded_second = rest.split('.')
            if len(diveded_second) == 1:
                seconds_str = diveded_second[0]
                ms_str = "0"
            else:
                seconds_str, ms_str = diveded_second[:2]
            try:
                minutes = int(minutes_str)
                seconds = int(seconds_str)
                ms = int(ms_str)
                if len(ms_str) == 2:
                    ms *= 10
                timing = (minutes * 60000) + (seconds * 1000) + ms
                lrc_lines.append({'ms': timing, 'content': content.strip()})
            except ValueError:
                pass
    return lrc_lines


"""Parse native character-framed cron output without guessing log headings."""
import re


def response_body(data, job_id):
    """Accept the native character-framed document, never guess at log delimiters."""
    text = data.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n')
    header = re.match(r'\A# Cron Job: [^\n]+\n\n\*\*Job ID:\*\* ([A-Za-z0-9_-]+)\n'
                      r'\*\*Run Time:\*\* [^\n]+\n\*\*Schedule:\*\* [^\n]+\n\n'
                      r'\*\*Prompt Characters:\*\* ([0-9]{1,6})\n## Prompt\n\n', text)
    if not header or header[1] != job_id:
        raise ValueError('unknown output envelope')
    tail = text[header.end() + int(header[2]):]
    frame = re.match(r'\n\n\*\*Response Characters:\*\* ([0-9]{1,6})\n## Response\n\n', tail)
    if not frame:
        raise ValueError('unknown response frame')
    response = tail[frame.end():]
    if not response.endswith('\n') or len(response) != int(frame[1]) + 1 or not response[:-1].strip():
        raise ValueError('incomplete response frame')
    return response[:-1]

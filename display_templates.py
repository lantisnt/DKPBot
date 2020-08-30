def SingleEmbed(author_name, title, description, thumbnail_url, color, footer_text)
    _dict = {}
    if author_name:
        _dict['author'] = { 'name' : author_name }
        _dict['title'] = title
        _dict['description'] = description
        _dict['type'] = "rich"
        _dict['thumbnail']= { 'url' : thumbnail_url },
        'color'         : color,
        'footer'        : {
            'text' : footer_text
        },
        'fields' : []
    }

    return _dict
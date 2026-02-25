import sys
sys.path.append('.')
try:
    from app.tg_bot import application
    handlers = application.handlers
    print('Registered handlers:')
    for group in handlers:
        for handler in handlers[group]:
            if hasattr(handler, 'commands'):
                print(f'  Command: /{handler.commands} (group {group})')
            else:
                print(f'  Other handler: {handler.__class__.__name__}')
except Exception as e:
    print(f'Error importing bot: {e}')


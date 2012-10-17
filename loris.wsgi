#!/usr/bin/env python
import sys
sys.path.append('/var/www/loris/loris')

from app import create_app
application = create_app()
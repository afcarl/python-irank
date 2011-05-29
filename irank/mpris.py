#!/usr/bin/env python
import os, sys, re, time, urllib2, dbus, gobject

METADATA = 'Metadata'
URL_PROPERTY = 'xesam:url'

mpris_prefix="org.mpris.MediaPlayer2."
PLAYER = 'org.mpris.MediaPlayer2.Player'
mpris_object="/org/mpris/MediaPlayer2"

def init_glib():
	if not init_glib.called:
		init_glib.called = True
	from dbus.mainloop.glib import DBusGMainLoop
	DBusGMainLoop(set_as_default=True)
init_glib.called = False

class Player(object):
	@classmethod
	def bus(cls):
		init_glib()
		return dbus.SessionBus()

	def __init__(self, name=None):
		init_glib()
		bus = dbus.SessionBus()
		self.player_name = name or os.environ.get('MPRIS_REMOTE_PLAYER', None) or type(self).guess_player_name()
		player_namespace = mpris_prefix + self.player_name
		player_obj = bus.get_object(player_namespace, mpris_object)

		self.player = dbus.Interface(player_obj, dbus_interface=PLAYER)
		self.properties = dbus.Interface(player_obj, dbus_interface=dbus.PROPERTIES_IFACE)

	@property
	def metadata(self):
		return self.properties.GetAll(PLAYER)[METADATA]

	@property
	def track(self):
		uri = self.metadata[URL_PROPERTY]
		try:
			return _path(uri)
		except ValueError:
			print "Invalid URI: %r" % (uri,)
			raise

	def each_track(self, cb):
		def playing_uri_changed(source, properties, signature):
			try:
				uri = properties[METADATA][URL_PROPERTY]
			except KeyError:
				return
			cb(_path(uri))

		self.properties.connect_to_signal('PropertiesChanged', playing_uri_changed)
		cb(self.track)
		loop = gobject.MainLoop()
		loop.run()
	
	def __repr__(self):
		return '<mpris.Player (%s)>' % (self.player_name,)

	@classmethod
	def possible_names(cls):
		return [ name[len(mpris_prefix):] for name in cls.bus().list_names() if name.startswith(mpris_prefix) ]

	# returns first matching player
	@classmethod
	def guess_player_name(cls):
		names = cls.possible_names()
		if not names:
			print >>sys.stderr, "No MPRIS-compliant player found running."
			raise SystemExit(1)
		return names[0]

def _path(uri):
	transport, path = urllib2.splittype(uri)
	if transport != 'file':
		raise ValueError("%r type is not 'file'" % (transport,))
	return urllib2.unquote(path[2:]).encode('utf-8')


if __name__ == '__main__':
	def _(s):
		print repr(s)
	player = Player()
	print "Monitoring track details from %s..." % (player.player_name,)
	try:
		player.each_track(_)
	except KeyboardInterrupt: pass
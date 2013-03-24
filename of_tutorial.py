# Copyright 2012 James McCauley
#
# This file is part of POX.
#
# POX is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# POX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with POX.  If not, see <http://www.gnu.org/licenses/>.

"""
This component is for use with the OpenFlow tutorial.

It acts as a simple hub, but can be modified to act like an L2
learning switch.

It's quite similar to the one for NOX.  Credit where credit due. :)
"""

from pox.core import core
from pox.lib.util import dpidToStr
import pox.openflow.libopenflow_01 as of
from pox.lib.addresses import EthAddr
from pox.lib.addresses import IPAddr
from pox.openflow.of_json import *
import pox.misc.Stats as s

log = core.getLogger()

#global stats1
#stats1=[]

class Tutorial (object):
  """
  A Tutorial object is created for each switch that connects.
  A Connection object for that switch is passed to the __init__ function.
  """
  def __init__ (self, connection):
    # Keep track of the connection to the switch so that we can
    # send it messages!
    self.connection = connection

    # This binds our PacketIn event listener
    connection.addListeners(self)
    #for con in core.openflow.connections:
     # msg = of.ofp_queue_stats_request()
     # msg.port_no = of.OFPP_ALL
     # msg.queue_id = of.OFPQ_ALL
     # con.send(of.ofp_stats_request(body=msg))

    # Use this table to keep track of which ethernet address is on
    # which switch port (keys are MACs, values are ports).
    self.mac_to_port = {}


  def resend_packet (self, packet_in, out_port):
    """
    Instructs the switch to resend a packet that it had sent to us.
    "packet_in" is the ofp_packet_in object the switch had sent to the
    controller due to a table-miss.
    """
    msg = of.ofp_packet_out()
    msg.data = packet_in

    # Add an action to send to the specified port
    action = of.ofp_action_output(port = out_port)
    msg.actions.append(action)

    # Send message to switch
    self.connection.send(msg)


  def act_like_hub (self, packet, packet_in):
    """
    Implement hub-like behavior -- send all packets to all ports besides
    the input port.
    """

    # We want to output to all ports -- we do that using the special
    # OFPP_ALL port as the output port.  (We could have also used
    # OFPP_FLOOD.)
    self.resend_packet(packet_in, of.OFPP_ALL)

    # Note that if we didn't get a valid buffer_id, a slightly better
    # implementation would check that we got the full data before
    # sending it (len(packet_in.data) should be == packet_in.total_len)).

  def act_like_switch (self, packet, packet_in):
    """
    Implement switch-like behavior.
    """

    srcaddr = EthAddr(packet.src)
    if not self.mac_to_port.has_key(srcaddr):
       self.mac_to_port[srcaddr] = packet_in.in_port

    for key, value in dict.items(self.mac_to_port):
       print key, value
    dstaddr = EthAddr(packet.dst)
    
    #if my_match.dl_dst in mac_t _port:
    if dstaddr in self.mac_to_port:
      # Send packet out the associated port
      out_port = self.mac_to_port[dstaddr]

      match = of.ofp_match()  
      msg = of.ofp_flow_mod() #creates a flow table entry in switc
      #msg.match.dl_src = srcaddr
      #msg.match.dl_dst = dstaddr
      msg.match.tp_dst = out_port

      for con in core.openflow.connections:
	msg2 = of.ofp_queue_stats_request()
        msg2.port_no = out_port
        msg2.queue_id = of.OFPQ_ALL
        con.send(of.ofp_stats_request(body=msg2))
	
      # Add an action to send to the specified port
      action = of.ofp_action_output(port = of.OFPP_CONTROLLER) 
      msg.actions.append(action)
	  
      queue_action = of.ofp_action_enqueue()
      queue_action.port = out_port
      queue_action.queue_id = 1
      msg.actions.append(queue_action)

      print "printing q stats in act like switch\n"
      #global stats1
      #print ("%s",s.stats)
      for f in s.stats:
		print f

      print "\n"

      # Send message to switch
      self.connection.send(msg)


      self.resend_packet(packet_in,out_port)

      
    else:
      # Flood the packet out everything but the input port
      # This part looks familiar, right?
      self.resend_packet (packet_in,of.OFPP_FLOOD)
      print "------flood-------"


  def _handle_PacketIn (self, event):
    """
    Handles packet in messages from the switch.
    """

    packet = event.parsed # This is the parsed packet data.
    if not packet.parsed:
      log.warning("Ignoring incomplete packet")
      return

    packet_in = event.ofp # The actual ofp_packet_in message.

    # Comment out the following line and uncomment the one after
    # when starting the exercise.
    #self.act_like_hub(packet, packet_in)
    self.act_like_switch(packet, packet_in)



def launch ():
  """
  Starts the component
  """
  def start_switch (event):
    log.debug("Controlling %s" % (event.connection,))
    Tutorial(event.connection)
  
  def handle_queue_stats (event):
    log.info("inside queue_stats")
    #global stats1
    s.stats = flow_stats_to_list(event.stats)
    log.debug("QueueStatsReceived from %s: %s", 
    dpidToStr(event.connection.dpid), s.stats)
   # self.resend_packet(packet_in,out_port)

  def handle_port_stats (event):
    log.info("inside port stats")
    stats = flow_stats_to_list(event.stats)
    log.debug("PortStatsReceived from %s: %s",
    dpidToStr(event.connection.dpid), stats)

  def handle_flow_stats (event):
    log.info("inside table stats")
    #for f in event.stats:
     # print f.match
      #print f.instructions
    stats = flow_stats_to_list(event.stats)
    log.debug("TableStatsReceived from %s: %s",
    dpidToStr(event.connection.dpid), stats)


  core.openflow.addListenerByName("ConnectionUp", start_switch)
  core.openflow.addListenerByName("QueueStatsReceived", handle_queue_stats)
  core.openflow.addListenerByName("PortStatsReceived", handle_port_stats)
  #core.openflow.addListenerByName("TableStatsReceived", handle_table_stats)
  core.openflow.addListenerByName("FlowStatsReceived", handle_flow_stats)
  

# GNU GENERAL PUBLIC LICENSE -  Version 2, June 1991
# See LICENCE and README file for details

from collections import namedtuple
import time
from __builtin__ import long
from SMABluetoothPacket import SMABluetoothPacket
from SMANET2PlusPacket import SMANET2PlusPacket
from datetime import datetime

__author__ = 'Stuart Pittaway'

# Background Reading
# https://groups.google.com/forum/#!topic/sma-bluetooth/UP4Tp8Ob3OA
# https://github.com/Rincewind76/SMAInverter/blob/master/76_SMAInverter.pm
# https://sbfspot.codeplex.com/ (credit back to myself!!)

def Read_Level1_Packet_From_BT_Stream(btSocket,mylocalBTAddress=bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x00])):
    while True:
        #print "Waiting for SMA level 1 packet from Bluetooth stream"
        start = btSocket.recv(1)

        # Need to add in some timeout stuff here
        while start != '\x7e':
            start = btSocket.recv(1)

        length1 = btSocket.recv(1)
        length2 = btSocket.recv(1)
        checksum = btSocket.recv(1)
        SrcAdd = bytearray(btSocket.recv(6))
        DestAdd = bytearray(btSocket.recv(6))

        packet = SMABluetoothPacket(length1, length2, checksum, btSocket.recv(1), btSocket.recv(1), SrcAdd, DestAdd)

        # Read the whole byte stream unaltered (this contains ESCAPED characters)
        b = bytearray(btSocket.recv(packet.TotalPayloadLength()))

        # Populate the SMABluetoothPacket object with the bytes
        packet.pushEscapedByteArray(b)

        # Tidy up the packet lengths
        packet.finish()

        if DestAdd == mylocalBTAddress and packet.ValidateHeaderChecksum():
            break

    return packet

def read_SMA_BT_Packet(btSocket, waitPacketNumber=0, waitForPacket=False, mylocalBTAddress=bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x00])):
    #if waitForPacket:
    #    print "Waiting for reply to packet number {0:02x}".format(waitPacketNumber)
    #else:
    #    print "Waiting for reply to any packet"

    bluetoothbuffer = Read_Level1_Packet_From_BT_Stream(btSocket,mylocalBTAddress)

    v = namedtuple("SMAPacket", ["levelone", "leveltwo"], verbose=False)
    v.levelone = bluetoothbuffer

    if bluetoothbuffer.containsLevel2Packet():
        # Instance to hold level 2 packet
        level2Packet = SMANET2PlusPacket()

        # Write the payload into a level2 class structure
        level2Packet.pushRawByteArray(bluetoothbuffer.getLevel2Payload())

        if waitForPacket == True and level2Packet.getPacketCounter() != waitPacketNumber:
            print("Received packet number {0:02x} expected {1:02x}".format(level2Packet.getPacketCounter(),
                                                                           waitPacketNumber))
            raise Exception("Wrong Level 2 packet returned!")

        # if bluetoothbuffer.CommandCode() == 0x0008:
            # print "Level 2 packet length (according to packet): %d" % level2Packet.totalCalculatedPacketLength()

        # Loop until we have the entire packet rebuilt (may take several/hundreds of level 1 packets)
        while (bluetoothbuffer.CommandCode() != 0x0001) and (bluetoothbuffer.lastByte() != 0x7e):
            bluetoothbuffer = Read_Level1_Packet_From_BT_Stream(btSocket,mylocalBTAddress)
            level2Packet.pushRawByteArray(bluetoothbuffer.getLevel2Payload())
            v.levelone = bluetoothbuffer

        if not level2Packet.isPacketFull():
            raise Exception("Failed to grab all the bytes needed for a Level 2 packet")

        if not level2Packet.validateChecksum(bluetoothbuffer.getLevel2Checksum()):
            raise Exception("Invalid checksum on Level 2 packet")

        v.leveltwo = level2Packet

        # Output the level2 payload (after its been combined from multiple packets if needed)
        #print level2Packet.debugViewPacket()
    return v

def LogMessageWithByteArray(message, ba):
    """Simple output of message and bytearray data in hex for debugging"""
    print("{0}:{1}".format(message.rjust(21), ByteToHex(ba)))


def ByteToHex(byteStr):
    """Convert a byte string to it's hex string representation e.g. for output."""
    return ''.join(["%02X " % x  for x in byteStr])

def BTAddressToByteArray(hexStr, sep):
    """Convert a  hex string containing seperators to a bytearray object"""
    b = bytearray()
    for i in hexStr.split(sep):
        b.append(int(i, 16))
    return b

def encodeInverterPassword(InverterPassword):
    # """Encodes InverterPassword (digit number) into array for passing to SMA protocol"""
    if len(InverterPassword) > 12:
        raise Exception("Password can only be up to 12 digits in length")

    a = bytearray(InverterPassword)

    for i in range( 12- len(a)):
        a.append(0)

    for i in range(len(a)):
        if a[i] == 0:
            a[i] = 0x88
        else:
            a[i] = (a[i] + 0x88) % 0xff

    return a

def floattobytearray(value):
    # Converts an float value into 4 single bytes inside a bytearray
    # useful for converting epoch dates
    b = bytearray()
    hexStr = "{0:08x}".format(long(value))
    b.append(chr(int (hexStr[0:2], 16)))
    b.append(chr(int (hexStr[2:4], 16)))
    b.append(chr(int (hexStr[4:6], 16)))
    b.append(chr(int (hexStr[6:8], 16)))

    b.reverse()
    return b

def spotvaluelist_dictionary():
    spotvaluelist = {}

    SpotValue=namedtuple("spotvalue", ["Description", "Units", "Scale"])

    spotvaluelist[0x0001] = SpotValue("InverterSerial","",1)
    spotvaluelist[0x0002] = SpotValue("InverterName","",None)
    spotvaluelist[0x263f] = SpotValue("ACTotalPower","Watts", 1)
    spotvaluelist[0x411e] = SpotValue("Ph1ACMax","Watts", 1)
    spotvaluelist[0x411f] = SpotValue("Ph2ACMax","Watts", 1)
    spotvaluelist[0x4120] = SpotValue("Ph3ACMax","Watts", 1)
    spotvaluelist[0x4640] = SpotValue("Ph1Power","Watts",1)
    spotvaluelist[0x4641] = SpotValue("Ph2Power","Watts",1)
    spotvaluelist[0x4642] = SpotValue("Ph3Power","Watts",1)
    spotvaluelist[0x4648] = SpotValue("Ph1ACVolt","Volts",100)
    spotvaluelist[0x4649] = SpotValue("Ph2ACVolt","Volts",100)
    spotvaluelist[0x464a] = SpotValue("Ph3ACVolt","Volts",100)
    spotvaluelist[0x4650] = SpotValue("Ph1ACCurrent","Amps",1000)
    spotvaluelist[0x4651] = SpotValue("Ph2ACCurrent","Amps",1000)
    spotvaluelist[0x4652] = SpotValue("Ph3ACCurrent","Amps",1000)
    spotvaluelist[0x4657] = SpotValue("ACGridFreq","Hz",100)
    spotvaluelist[0x821e] = SpotValue("Inverter Name","TEXT",None)
    spotvaluelist[0x2601] = SpotValue("TotalYield","Wh",1)
    spotvaluelist[0x2622] = SpotValue("DayYield","Wh",1)
    spotvaluelist[0x462f] = SpotValue("FeedInTime","hours",3600)
    spotvaluelist[0x462e] = SpotValue("OperatingTime","hours",3600)
    spotvaluelist[0x251e] = SpotValue("DCPower1","Watts",1)
    spotvaluelist[0x451f] = SpotValue("DCVoltage1","Volts",100)
    spotvaluelist[0x4521] = SpotValue("DCCurrent1","Amps",1)

    spotvaluelist["unknown"]  = SpotValue("??","??",1)
    return spotvaluelist

def extract_spot_values(level2Packet, gap=40):
    powdata = level2Packet.getArray()

    spotvaluelist = spotvaluelist_dictionary()

    SpotValueOutput=namedtuple("SpotValueOutput", ["Label", "Value"])

    #Return a dictionary
    outputlist = {}

    if len(powdata) > 0:
        for i in range(40, len(powdata), gap):
            # LogMessageWithByteArray("PowData", powdata[i:i+gap])

            valuetype = level2Packet.getTwoByteLong(i + 1)
            #idate = level2Packet.getFourByteLong(i + 4)
            #t = time.localtime(long(idate))

            if valuetype in spotvaluelist:
                spotvalue = spotvaluelist[valuetype]
            else:
                spotvalue = spotvaluelist["unknown"]
                valuetype = 0

            if spotvalue.Units == "TEXT":
                value = powdata[i + 8:i + 22].decode("utf-8")
            elif spotvalue.Units == "hours":
                value = level2Packet.getFourByteDouble(i + 8)
                if value is not None:
                    value = value / spotvalue.Scale
            elif spotvalue.Units == "Wh":
                value = level2Packet.getFourByteDouble(i + 8)
            else:
                value = level2Packet.getThreeByteDouble(i + 8)
                if value is not None:
                    value = value / spotvalue.Scale

            #if i == 40:
            #    outputlist.append( (0, time.strftime("%Y-%m-%d %H:%M:%S",t))  )

            #print "{0} {1:04x} {2} '{3}' {4} {5}".format(time.asctime(t), valuetype, spotvalue.Description, value, spotvalue.Units, level2Packet.getThreeByteDouble(i + 8 + 4))

            if value is None:
                value=0.0

            #outputlist.append( SpotValueOutput(valuetype,spotvalue.Description, value)  )
            outputlist[valuetype] = SpotValueOutput(spotvalue.Description, value)
    return outputlist


def getInverterName(btSocket, packet_send_counter, mylocalBTAddress, InverterCodeArray, AddressFFFFFFFF):
    send9 = SMABluetoothPacket(1, 1, 0x00, 0x01, 0x00, mylocalBTAddress, AddressFFFFFFFF)
    pluspacket9 = SMANET2PlusPacket(0x09, 0xA0, packet_send_counter, InverterCodeArray, 0x00, 0x00, 0x00)
    pluspacket9.pushRawByteArray(bytearray([0x00, 0x02, 0x00,
                                            0x58, 0x00, 0x1e, 0x82,
                                            0x00, 0xFF, 0x1e, 0x82
                                           ,0x00]))
    send9.pushRawByteArray(pluspacket9.getBytesForSending())
    send9.finish()
    send9.sendPacket(btSocket)
    bluetoothbuffer = read_SMA_BT_Packet(btSocket, packet_send_counter, True,mylocalBTAddress)
    if bluetoothbuffer.leveltwo.errorCode() > 0:
        print("Error code returned from inverter")

    valuetype = bluetoothbuffer.leveltwo.getTwoByteLong(40 + 1)
    # idate = bluetoothbuffer.leveltwo.getFourByteLong(40 + 4)
    # t = time.localtime(long(idate))
    if valuetype == 0x821e:
        value = bluetoothbuffer.leveltwo.getArray()[40 + 8:40 + 8 + 14].decode("utf-8")
    else:
        value = ""

    return value

def logon(btSocket,mylocalBTAddress,AddressFFFFFFFF,InverterCodeArray,packet_send_counter, InverterPasswordArray):
    # Logon to inverter
    pluspacket1 = SMANET2PlusPacket(0x0e, 0xa0, packet_send_counter, InverterCodeArray,  0x00,  0x01, 0x01)
    pluspacket1.pushLong(0xFFFD040c)
    #0x07 = User logon, 0x0a = installer logon
    pluspacket1.pushLong(0x00000007)
    pluspacket1.pushLong(0x00000384)
    pluspacket1.pushRawByteArray( floattobytearray(time.mktime(datetime.today().timetuple())))
    pluspacket1.pushLong(0x00000000)
    pluspacket1.pushRawByteArray(InverterPasswordArray)
    send = SMABluetoothPacket(1, 1, 0x00, 0x01, 0x00, mylocalBTAddress, AddressFFFFFFFF)
    send.pushRawByteArray(pluspacket1.getBytesForSending())
    send.finish()
    send.sendPacket(btSocket)

    bluetoothbuffer = read_SMA_BT_Packet(btSocket, packet_send_counter, True, mylocalBTAddress)

    checkPacketReply(bluetoothbuffer, 0x0001)
    if bluetoothbuffer.leveltwo.errorCode() > 0:
        raise Exception("Error code returned from inverter - during logon - wrong password?")



def initaliseSMAConnection(btSocket,mylocalBTAddress,AddressFFFFFFFF,InverterCodeArray,packet_send_counter):
    # Wait for 1st message from inverter to arrive (should be an 0002 command)
    bluetoothbuffer = read_SMA_BT_Packet(btSocket,mylocalBTAddress)
    checkPacketReply(bluetoothbuffer,0x0002);

    netid = bluetoothbuffer.levelone.getByte(4);
    #print "netid=%02x" % netid
    inverterAddress = bluetoothbuffer.levelone.SourceAddress;

    # Reply to 0x0002 cmd with our data
    send = SMABluetoothPacket(0x1f, 0x00, 0x00, 0x02, 0x00, mylocalBTAddress, inverterAddress);
    send.pushUnescapedByteArray( bytearray([0x00, 0x04, 0x70, 0x00, netid, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00]) )
    send.finish()
    # print send.DisplayPacketDebugInfo("Reply to 0x02 cmd")
    send.sendPacket(btSocket);

    # Receive 0x000a cmd
    bluetoothbuffer = read_SMA_BT_Packet(btSocket,mylocalBTAddress);
    checkPacketReply(bluetoothbuffer,0x000a);

    # Receive 0x000c cmd (sometimes this doesnt turn up!)
    bluetoothbuffer = read_SMA_BT_Packet(btSocket,mylocalBTAddress);
    if bluetoothbuffer.levelone.CommandCode() != 0x0005 and bluetoothbuffer.levelone.CommandCode() != 0x000c:
        print ("Expected different command 0x0005 or 0x000c");

    # Receive 0x0005 if we didnt get it above
    if bluetoothbuffer.levelone.CommandCode() != 0x0005:
        bluetoothbuffer = read_SMA_BT_Packet(btSocket,mylocalBTAddress)
        checkPacketReply(bluetoothbuffer,0x0005)

    # Now the fun begins...

    send = SMABluetoothPacket(0x3f, 0x00, 0x00, 0x01, 0x00, mylocalBTAddress, AddressFFFFFFFF)
    pluspacket1 = SMANET2PlusPacket(0x09, 0xa0, packet_send_counter, InverterCodeArray, 0, 0, 0)
    pluspacket1.pushRawByteArray(bytearray([0x00, 0x02, 0x00, 0x00]))
    pluspacket1.pushLong(0x00000000)
    pluspacket1.pushLong(0x00000000)
    send.pushRawByteArray(pluspacket1.getBytesForSending())
    send.finish()
    send.sendPacket(btSocket)

    bluetoothbuffer = read_SMA_BT_Packet(btSocket, packet_send_counter, True,mylocalBTAddress)
    checkPacketReply(bluetoothbuffer,0x0001)
    if bluetoothbuffer.leveltwo.errorCode() > 0:
        print("Error code returned from inverter")

    packet_send_counter += 1

    inverterSerial = bluetoothbuffer.leveltwo.getDestinationAddress()

    send = SMABluetoothPacket(0x3b, 0, 0x00, 0x01, 0x00, mylocalBTAddress, AddressFFFFFFFF)
    pluspacket1 = SMANET2PlusPacket(0x08, 0xa0, packet_send_counter, InverterCodeArray, 0x00, 0x03, 0x03)
    pluspacket1.pushRawByteArray(bytearray([0x0E, 0x01, 0xFD, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF ]))
    send.pushRawByteArray(pluspacket1.getBytesForSending())
    send.finish()
    send.sendPacket(btSocket)

    packet_send_counter += 1

def checkPacketReply(bluetoothbuffer,commandcode):
    if bluetoothbuffer.levelone.CommandCode() != commandcode:
        raise Exception("Expected command 0x{0:04x} received 0x{1:04x}".format(commandcode,bluetoothbuffer.levelone.CommandCode()))

#def pause():
#    # Sleep to half second to prevent SMA inverter being drowned by our traffic
#    # (seems to work okay without delay but older inverters may suffer)
#    time.sleep(0.5)

def request_data(btSocket, packet_send_counter, mylocalBTAddress, InverterCodeArray, AddressFFFFFFFF, cmd, first, last):
    send9 = SMABluetoothPacket(0x01, 0x01, 0x00, 0x01, 0x00, mylocalBTAddress, AddressFFFFFFFF)
    pluspacket9 = SMANET2PlusPacket(0x09, 0xA0, packet_send_counter, InverterCodeArray, 0x00, 0x00, 0x00)
    pluspacket9.pushLong(cmd)
    pluspacket9.pushLong(first)
    pluspacket9.pushLong(last)
    send9.pushRawByteArray(pluspacket9.getBytesForSending())
    send9.finish()
    send9.sendPacket(btSocket)
    bluetoothbuffer = read_SMA_BT_Packet(btSocket, packet_send_counter, True,mylocalBTAddress)

    if bluetoothbuffer.leveltwo.errorCode() > 0:
        return None

    leveltwo=bluetoothbuffer.leveltwo

    if leveltwo.errorCode() == 0:
        return leveltwo

    return None

def toVolt(value):
    return float(value) / float(100.0)

def toHours(value):
    return float(value) / float(3600)

def extract_data(level2Packet):
    #Return a dictionary
    outputlist = {}

    SpotValueOutput=namedtuple("SpotValueOutput", ["Label", "Value"])


    #Start here
    offset = 40

    if (level2Packet.totalPayloadLength()==0):
        return outputlist

    while (offset < level2Packet.totalPayloadLength()):
        recordSize=28
        value=0
        classtype = level2Packet.getByte(offset)
        #classtype should always be =1
        readingtype = level2Packet.getTwoByteLong(offset+1)
        dataType = level2Packet.getByte(offset+3)
        datetime = level2Packet.getFourByteLong(offset+4)

        if (readingtype==0):
            break;

        if (dataType != 0x10) and (dataType != 0x08):
            # Not TEXT or STATUS, so it should be DWORD
            value = level2Packet.getTwoByteLong(offset+8)

            #Check for NULLs
            if (value == 0x8000) or (value == 0xFFFF):
                value = 0;


            #TODO MOVE THIS LOOP INTO A LOOK UP LIST TO AUTO READ THE VALUES AS NEEDED...

            # DC voltage input (aka SPOT_UDC1 / SPOT_UDC2)
            if (readingtype==0x451f):
                if (classtype==1):
                    outputlist["SPOT_UDC1"] = SpotValueOutput("SPOT_UDC1".format(readingtype), toVolt(value))
                if (classtype==2):
                    outputlist["SPOT_UDC2"] = SpotValueOutput("SPOT_UDC2".format(readingtype), toVolt(value))

            # Power L1 (aka SPOT_PAC1)
            if (readingtype==0x4640):
                outputlist["SPOT_PAC1"] = SpotValueOutput("SPOT_PAC1".format(readingtype), toVolt(value))

            # Power L2 (aka SPOT_PAC2)
            if (readingtype==0x4641):
                outputlist["SPOT_PAC2"] = SpotValueOutput("SPOT_PAC2".format(readingtype), toVolt(value))

            # Power L3 (aka SPOT_PAC3)
            if (readingtype==0x4642):
                outputlist["SPOT_PAC3"] = SpotValueOutput("SPOT_PAC3".format(readingtype), toVolt(value))

            # Grid frequency (aka SPOT_FREQ)
            if (readingtype==0x4657):
                outputlist["SPOT_FREQ"] = SpotValueOutput("SPOT_FREQ".format(readingtype), value)

            # Power (aka SPOT_PACTOT)
            if (readingtype==0x263F):
                outputlist["SPOT_PACTOT"] = SpotValueOutput("SPOT_PACTOT".format(readingtype), value)

            #Operating condition temperatures
            if (readingtype==0x2377):
                outputlist["OP_TEMP"] = SpotValueOutput("OP_TEMP".format(readingtype), value)

            #  Total yield (aka SPOT_ETOTAL)
            if (readingtype==0x2601):
                value=level2Packet.get8ByteFloat(offset+8)
                recordSize=16
                outputlist["SPOT_ETOTAL"] = SpotValueOutput("SPOT_ETOTAL".format(readingtype), value)

            # Day yield (aka SPOT_ETODAY)
            if (readingtype==0x2622):
                value=level2Packet.get8ByteFloat(offset+8)
                recordSize=16
                outputlist["SPOT_ETODAY"] = SpotValueOutput("SPOT_ETODAY".format(readingtype), value)

            #Operating time (aka SPOT_OPERTM)
            if (readingtype==0x462E):
                value=level2Packet.get8ByteFloat(offset+8)
                recordSize=16
                outputlist["SPOT_OPERTM"] = SpotValueOutput("SPOT_OPERTM".format(readingtype), toHours(value))

            #Feed-in time (aka SPOT_FEEDTM)
            if (readingtype==0x462F):
                value=level2Packet.get8ByteFloat(offset+8)
                recordSize=16
                outputlist["SPOT_FEEDTM"] = SpotValueOutput("SPOT_FEEDTM".format(readingtype), toHours(value))

            #Output to caller
            outputlist[readingtype] = SpotValueOutput("DebugX{0:04x}".format(readingtype), value)

        offset+=recordSize

    #Start 40 bytes into packet
    #for i in range(40, len(powdata), gap):

    return outputlist

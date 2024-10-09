import binascii
import struct

def decode_bcd(bcd_data):
        val = 0

        i = len(bcd_data)
        while i > 0:
            val = (val * 10)
            if bcd_data[i-1]>>4 < 0xA:
                val += ((bcd_data[i-1]>>4) & 0xF)
            val = (val * 10) + ( bcd_data[i-1] & 0xF)

            i -= 1

        if(bcd_data[len(bcd_data)-1]>>4 == 0xF):
            val *= -1

        return val

def decode_abb_telegram1(telegram):
    """Decode a telegram1 from an ABB meter."""
    energy_total = round(decode_bcd(telegram[22:28]) / 100, 2)

    data = {
      "energy_total": {
        "name": "Energy, total",
        "value": energy_total,
      },
    }

    return data

def decode_abb_telegram2(telegram):
    """Decode a telegram2 from an ABB meter."""
    """Information"""
    serial_number = binascii.hexlify(telegram[7:11]).decode('utf-8')
    version = int(telegram[13])
    access_number = int(telegram[15])
    status = int(telegram[16])

    """Active power"""
    active_power_total = round(struct.unpack('<i', telegram[22:26])[0] * 0.01, 3)
    active_power_l1 = round(struct.unpack('<i', telegram[31:35])[0] * 0.01, 3)
    active_power_l2 = round(struct.unpack('<i', telegram[40:44])[0] * 0.01, 3)
    active_power_l3 = round(struct.unpack('<i', telegram[49:53])[0] * 0.01, 3)

    """Voltage"""
    voltage_l1 = round(struct.unpack('<i', telegram[59:63])[0] * 0.1, 3)
    voltage_l2 = round(struct.unpack('<i', telegram[69:73])[0] * 0.1, 3)
    voltage_l3 = round(struct.unpack('<i', telegram[79:83])[0] * 0.1, 3)

    voltage_l1_l2 = round(struct.unpack('<i', telegram[89:93])[0] * 0.1, 3)
    voltage_l3_l2 = round(struct.unpack('<i', telegram[99:103])[0] * 0.1, 3)
    voltage_l1_l3 = round(struct.unpack('<i', telegram[109:113])[0] * 0.1, 3)

    """Frequency"""
    frequency = round(decode_bcd(telegram[147:149]) / 100, 2)

    """Current"""
    current_l1 = round(struct.unpack('<i', telegram[119:123])[0] * 0.01, 3)
    current_l2 = round(struct.unpack('<i', telegram[129:133])[0] * 0.01, 3)
    current_l3 = round(struct.unpack('<i', telegram[139:143])[0] * 0.01, 3)

    """Energy"""
    energy_l1 = round(decode_bcd(telegram[171:177]) / 100, 2)
    energy_l2 = round(decode_bcd(telegram[182:188]) / 100, 2)
    energy_l3 = round(decode_bcd(telegram[193:199]) / 100, 2)

    data = {
        "metadata": {
          "serial_number": serial_number,
          "version": version,
          "access_number": access_number,
          "status": status,
        },
        "active_power_total": {
          "name": "Active power, total",
          "value": active_power_total,
        },
        "active_power_l1": {
          "name": "Active power, L1",
          "value": active_power_l1,
        },
        "active_power_l2": {
          "name": "Active power, L2",
          "value": active_power_l2,
        },
        "active_power_l3": {
          "name": "Active power, L3",
          "value": active_power_l3,
        },
        "voltage_l1": {
          "name": "Voltage, L1",
          "value": voltage_l1,
        },
        "voltage_l2": {
          "name": "Voltage, L2",
          "value": voltage_l2,
        },
        "voltage_l3": {
          "name": "Voltage, L3",
          "value": voltage_l3,
        },
        "voltage_l1_l2": {
          "name": "Voltage, L1-L2",
          "value": voltage_l1_l2,
        },
        "voltage_l3_l2": {
          "name": "Voltage, L3-L2",
          "value": voltage_l3_l2,
        },
        "voltage_l1_l3": {
          "name": "Voltage, L1-L3",
          "value": voltage_l1_l3,
        },
        "frequency": {
          "name": "Frequency",
          "value": frequency,
          "unit_of_measurement": "Hz"
        },
        "current_l1": {
          "name": "Current, L1",
          "value": current_l1,
        },
        "current_l2": {
          "name": "Current, L2",
          "value": current_l2,
        },
        "current_l3": {
          "name": "Current, L3",
          "value": current_l3,
        },
        "energy_l1": {
          "name": "Energy, L1",
          "value": energy_l1,
        },
        "energy_l2": {
          "name": "Energy, L2",
          "value": energy_l2,
        },
        "energy_l3": {
          "name": "Energy, L3",
          "value": energy_l3,
        }
    }

    return data
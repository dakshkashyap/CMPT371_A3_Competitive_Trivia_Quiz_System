"""
questions.py
------------
Original networking quiz bank inspired by the topic coverage of
Computer Networking: A Top-Down Approach, 9th edition.

Each question is a dict with:
  - "question" : str
  - "options"  : list[str]
  - "answer"   : str
  - "category" : str
    - "explanation" : str
"""

QUESTIONS = [
    # -------------------------------------------------------------------------
    # Fundamentals
    # -------------------------------------------------------------------------
    {
        "question": "Which statement best describes a protocol in computer networking?",
        "options": [
            "A) A hardware device that forwards packets",
            "B) A set of rules defining message format, order, and actions taken",
            "C) A physical cable standard used in LANs",
            "D) A security tool that blocks malicious traffic"
        ],
        "answer": "B",
        "category": "Fundamentals",
        "explanation": "A protocol is a shared rulebook for communication: it defines message format, order, and what each side does when sending or receiving specific messages."
    },
    {
        "question": "What is encapsulation?",
        "options": [
            "A) Encrypting application data before transmission",
            "B) Breaking a message into equal-sized segments only",
            "C) Wrapping data with protocol headers as it moves down the layers",
            "D) Dropping packets that exceed the router queue"
        ],
        "answer": "C",
        "category": "Fundamentals",
        "explanation": "Encapsulation means each lower layer adds its own header (and sometimes trailer) as data moves down the stack, enabling addressing, reliability, and forwarding."
    },
    {
        "question": "Which switching approach reserves resources for the duration of a communication session?",
        "options": [
            "A) Packet switching",
            "B) Circuit switching",
            "C) Statistical multiplexing",
            "D) Best-effort forwarding"
        ],
        "answer": "B",
        "category": "Fundamentals",
        "explanation": "Circuit switching pre-allocates path resources for the whole session, unlike packet switching which shares links statistically among many flows."
    },
    {
        "question": "If a router's output queue becomes full, what is the most likely immediate result?",
        "options": [
            "A) Packets are automatically encrypted",
            "B) Packets are fragmented into smaller packets",
            "C) Newly arriving packets may be dropped",
            "D) The sender switches from TCP to UDP"
        ],
        "answer": "C",
        "category": "Fundamentals",
        "explanation": "When an output queue is full, newly arriving packets cannot be buffered and are dropped; this is a direct cause of loss under congestion."
    },

    # -------------------------------------------------------------------------
    # Application Layer
    # -------------------------------------------------------------------------
    {
        "question": "Which application-layer protocol is primarily used to retrieve web pages?",
        "options": [
            "A) DNS",
            "B) HTTP",
            "C) SMTP",
            "D) ARP"
        ],
        "answer": "B",
        "category": "Application Layer",
        "explanation": "HTTP is the web transfer protocol used by browsers and servers to request and deliver web resources."
    },
    {
        "question": "What is a main advantage of persistent HTTP connections over non-persistent ones?",
        "options": [
            "A) They eliminate the need for IP addresses",
            "B) They allow multiple objects to be sent over fewer TCP connections",
            "C) They always provide built-in encryption",
            "D) They replace DNS entirely"
        ],
        "answer": "B",
        "category": "Application Layer",
        "explanation": "Persistent connections reuse one TCP connection for multiple objects, reducing handshake overhead and latency compared with opening a new connection per object."
    },
    {
        "question": "What is the primary job of DNS?",
        "options": [
            "A) Mapping domain names to resource records such as IP addresses",
            "B) Encrypting packets between routers",
            "C) Detecting bit errors at the link layer",
            "D) Reserving bandwidth for video streams"
        ],
        "answer": "A",
        "category": "Application Layer",
        "explanation": "DNS resolves human-readable names to resource records such as IP addresses so clients can reach hosts."
    },
    {
        "question": "Which protocol is mainly used to transfer email from a sender's mail server onward?",
        "options": [
            "A) HTTP",
            "B) SMTP",
            "C) IMAP",
            "D) DHCP"
        ],
        "answer": "B",
        "category": "Application Layer",
        "explanation": "SMTP is the server-to-server email transfer protocol used to relay outgoing mail across the Internet."
    },
    {
        "question": "What is the main role of a content distribution network (CDN)?",
        "options": [
            "A) To assign MAC addresses to hosts",
            "B) To store backups of router configurations only",
            "C) To deliver content from geographically distributed servers closer to users",
            "D) To replace the transport layer with an application-layer protocol"
        ],
        "answer": "C",
        "category": "Application Layer",
        "explanation": "A CDN places cached content at geographically distributed edge servers to reduce latency and improve delivery performance for users."
    },
    {
        "question": "QUIC is most closely associated with which transport foundation?",
        "options": [
            "A) UDP",
            "B) TCP",
            "C) ICMP",
            "D) ARP"
        ],
        "answer": "A",
        "category": "Application Layer",
        "explanation": "QUIC runs over UDP and implements reliability, congestion control, and security in user space, enabling faster connection setup."
    },

    # -------------------------------------------------------------------------
    # Transport Layer
    # -------------------------------------------------------------------------
    {
        "question": "What field is essential for transport-layer multiplexing and demultiplexing?",
        "options": [
            "A) TTL",
            "B) Port number",
            "C) MAC address",
            "D) VLAN ID"
        ],
        "answer": "B",
        "category": "Transport Layer",
        "explanation": "Port numbers let transport protocols deliver incoming segments to the correct application process on a host."
    },
    {
        "question": "Which transport protocol provides connectionless service?",
        "options": [
            "A) TCP",
            "B) UDP",
            "C) TLS",
            "D) HTTP/2"
        ],
        "answer": "B",
        "category": "Transport Layer",
        "explanation": "UDP is connectionless: it sends datagrams without handshake, retransmission, or in-order guarantees."
    },
    {
        "question": "Why does TCP use sequence numbers?",
        "options": [
            "A) To identify the router that forwarded the segment",
            "B) To support reliable, ordered data delivery",
            "C) To assign IP addresses dynamically",
            "D) To compress application data"
        ],
        "answer": "B",
        "category": "Transport Layer",
        "explanation": "Sequence numbers let TCP detect loss, reorder out-of-order data, and provide reliable byte-stream delivery."
    },
    {
        "question": "What problem is flow control designed to prevent?",
        "options": [
            "A) Router loops in the control plane",
            "B) A fast sender overwhelming a slow receiver",
            "C) DNS servers returning stale records",
            "D) MAC address duplication on Ethernet"
        ],
        "answer": "B",
        "category": "Transport Layer",
        "explanation": "Flow control protects the receiver by limiting how much unacknowledged data a sender can have in flight."
    },
    {
        "question": "Which reliable data transfer protocol may resend a whole window after one loss?",
        "options": [
            "A) Selective Repeat",
            "B) Go-Back-N",
            "C) DNS round-robin",
            "D) ARQ-free streaming"
        ],
        "answer": "B",
        "category": "Transport Layer",
        "explanation": "Go-Back-N retransmits from the first missing packet onward, which can cause many already-sent packets to be resent."
    },
    {
        "question": "What is the main goal of congestion control?",
        "options": [
            "A) To keep the sender from overrunning the receiver buffer only",
            "B) To prevent the network from becoming overloaded",
            "C) To translate private IP addresses into public ones",
            "D) To verify user identity at login"
        ],
        "answer": "B",
        "category": "Transport Layer",
        "explanation": "Congestion control aims to keep the network stable and efficient by reducing sending rates when paths become overloaded."
    },

    # -------------------------------------------------------------------------
    # Network Layer
    # -------------------------------------------------------------------------
    {
        "question": "What is the difference between forwarding and routing?",
        "options": [
            "A) Forwarding chooses a network-wide path, routing moves a packet out one interface",
            "B) Forwarding is per-router packet movement, routing is path computation across the network",
            "C) They are exactly the same concept",
            "D) Forwarding happens only in hosts, routing happens only in switches"
        ],
        "answer": "B",
        "category": "Network Layer",
        "explanation": "Forwarding is the per-router data-plane action of sending a packet out an interface; routing is the control-plane computation of end-to-end paths and forwarding tables."
    },
    {
        "question": "What is the main purpose of NAT in many home networks?",
        "options": [
            "A) To convert TCP traffic into UDP traffic",
            "B) To allow multiple devices to share a smaller number of public IP addresses",
            "C) To eliminate the need for DNS",
            "D) To authenticate users to Wi-Fi"
        ],
        "answer": "B",
        "category": "Network Layer",
        "explanation": "NAT rewrites address/port mappings so many private hosts can share one or a few public IPv4 addresses."
    },
    {
        "question": "Which protocol is commonly used for routing between different autonomous systems on the Internet?",
        "options": [
            "A) OSPF",
            "B) BGP",
            "C) ARP",
            "D) Ethernet"
        ],
        "answer": "B",
        "category": "Network Layer",
        "explanation": "BGP is the inter-domain routing protocol used to exchange reachability and policy between autonomous systems."
    },
    {
        "question": "Which protocol is widely used for intra-AS routing within an autonomous system?",
        "options": [
            "A) BGP",
            "B) OSPF",
            "C) TLS",
            "D) SMTP"
        ],
        "answer": "B",
        "category": "Network Layer",
        "explanation": "OSPF is a link-state interior gateway protocol commonly used inside one AS to compute shortest paths."
    },
    {
        "question": "What is ICMP primarily used for?",
        "options": [
            "A) Sending web objects",
            "B) Carrying encrypted email",
            "C) Reporting network control and error information",
            "D) Assigning transport-layer port numbers"
        ],
        "answer": "C",
        "category": "Network Layer",
        "explanation": "ICMP carries network diagnostics and error reporting messages, such as destination unreachable or time exceeded."
    },

    # -------------------------------------------------------------------------
    # Link Layer and LANs
    # -------------------------------------------------------------------------
    {
        "question": "What is the purpose of ARP in an IPv4 LAN?",
        "options": [
            "A) To map an IP address to a MAC address",
            "B) To map a MAC address to a port number",
            "C) To map a domain name to an IP address",
            "D) To map a router to a subnet mask"
        ],
        "answer": "A",
        "category": "Link Layer",
        "explanation": "ARP resolves a local IPv4 address to a MAC address so frames can be delivered on an Ethernet LAN."
    },
    {
        "question": "Which error-detection technique is widely used in link-layer protocols and storage systems?",
        "options": [
            "A) Caesar cipher",
            "B) Cyclic Redundancy Check (CRC)",
            "C) Distance-vector update",
            "D) Sliding-window fairness"
        ],
        "answer": "B",
        "category": "Link Layer",
        "explanation": "CRC provides strong error-detection capability using polynomial checks, making it widely used for frame integrity."
    },
    {
        "question": "What is a key function of an Ethernet switch?",
        "options": [
            "A) It resolves domain names for clients",
            "B) It forwards frames based on link-layer addresses",
            "C) It performs end-to-end congestion control",
            "D) It creates TLS sessions for browsers"
        ],
        "answer": "B",
        "category": "Link Layer",
        "explanation": "An Ethernet switch learns MAC-to-port mappings and forwards frames only on the appropriate outgoing port."
    },
    {
        "question": "What is the main benefit of a VLAN?",
        "options": [
            "A) It increases the speed of DNS lookups",
            "B) It provides logical segmentation within a switched LAN",
            "C) It replaces IP addressing with MAC addressing",
            "D) It disables broadcast traffic entirely"
        ],
        "answer": "B",
        "category": "Link Layer",
        "explanation": "VLANs create logical Layer 2 segments over shared switch infrastructure, improving isolation and broadcast control."
    },

    # -------------------------------------------------------------------------
    # Wireless and Mobile
    # -------------------------------------------------------------------------
    {
        "question": "Wi-Fi is most closely associated with which IEEE family of standards?",
        "options": [
            "A) 802.3",
            "B) 802.11",
            "C) 802.15",
            "D) 802.1Q"
        ],
        "answer": "B",
        "category": "Wireless",
        "explanation": "Wi-Fi is standardized in IEEE 802.11, which defines wireless LAN PHY and MAC behavior."
    },
    {
        "question": "What makes wireless channels more challenging than wired channels?",
        "options": [
            "A) Wireless channels never experience interference",
            "B) Wireless channels are always full duplex",
            "C) Signal attenuation, interference, and fading are more significant",
            "D) Wireless hosts do not require addressing"
        ],
        "answer": "C",
        "category": "Wireless",
        "explanation": "Wireless links face higher attenuation, interference, and multipath fading, so signal quality varies more over time."
    },
    {
        "question": "In mobile networking, what does mobility support aim to preserve as a user changes attachment points?",
        "options": [
            "A) The physical cable type",
            "B) Ongoing connectivity despite movement",
            "C) The same MAC address vendor prefix only",
            "D) The exact same radio frequency in every location"
        ],
        "answer": "B",
        "category": "Wireless",
        "explanation": "Mobility mechanisms aim to keep sessions connected while users move between networks or access points."
    },

    # -------------------------------------------------------------------------
    # Security
    # -------------------------------------------------------------------------
    {
        "question": "Which cryptographic approach uses the same secret key for encryption and decryption?",
        "options": [
            "A) Symmetric-key cryptography",
            "B) Public-key cryptography",
            "C) Hash chaining",
            "D) Digital signature verification"
        ],
        "answer": "A",
        "category": "Security",
        "explanation": "Symmetric cryptography uses one shared secret key for both encryption and decryption, making it fast for bulk data."
    },
    {
        "question": "What is the main purpose of a cryptographic hash in network security?",
        "options": [
            "A) To assign IP addresses securely",
            "B) To create a fixed-size digest useful for integrity checks",
            "C) To replace routing tables",
            "D) To guarantee packet delivery"
        ],
        "answer": "B",
        "category": "Security",
        "explanation": "A cryptographic hash maps data to a fixed-size digest used to detect tampering and verify integrity."
    },
    {
        "question": "What protocol is commonly used to secure HTTP connections on the modern web?",
        "options": [
            "A) FTP",
            "B) TLS",
            "C) ICMP",
            "D) ARP"
        ],
        "answer": "B",
        "category": "Security",
        "explanation": "TLS provides confidentiality, integrity, and authentication for HTTPS traffic between client and server."
    },
    {
        "question": "What is the main role of a firewall?",
        "options": [
            "A) To physically amplify wireless signals",
            "B) To filter traffic according to security rules",
            "C) To compress video for streaming",
            "D) To generate DNS records automatically"
        ],
        "answer": "B",
        "category": "Security",
        "explanation": "A firewall enforces security policy by allowing or blocking traffic based on rule conditions such as address, port, and protocol."
    },
    {
        "question": "An intrusion detection system (IDS) is mainly used to:",
        "options": [
            "A) Detect suspicious or malicious activity",
            "B) Assign MAC addresses to hosts",
            "C) Compute shortest paths between routers",
            "D) Replace end-point authentication"
        ],
        "answer": "A",
        "category": "Security",
        "explanation": "An IDS monitors hosts or networks to detect suspicious patterns and alert operators about potential attacks."
    }
]
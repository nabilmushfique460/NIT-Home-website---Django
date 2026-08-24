from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from products.models import Category, Product, ProductImage, ProductSpecification
from accounts.models import Address

class Command(BaseCommand):
    help = 'Seeds 10 PC Hardware Products, Categories, Specs, Images, and Admin/Demo Users'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting database seeding for N-IT Home...")

        # 1. Create Superuser & Demo User
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@nithome.com',
                password='admin12345',
                first_name='Admin',
                last_name='Director'
            )
            admin_user.profile.is_verified = True
            admin_user.profile.phone = '+880 1711-223344'
            admin_user.profile.save()
            self.stdout.write(self.style.SUCCESS("Created Superuser: admin / admin12345"))

        demo_user, created = User.objects.get_or_create(
            username='gamer_pro',
            defaults={
                'email': 'customer@nithome.com',
                'first_name': 'Nabil',
                'last_name': 'Hasan',
            }
        )
        if created:
            demo_user.set_password('customer123')
            demo_user.save()
            demo_user.profile.is_verified = True
            demo_user.profile.phone = '+880 1812-345678'
            demo_user.profile.save()

            Address.objects.create(
                user=demo_user,
                full_name='Nabil Hasan',
                phone='+880 1812-345678',
                street_address='House 42, Road 11, Block D, Banani',
                city='Dhaka',
                state_or_division='Dhaka Division',
                postal_code='1213',
                country='Bangladesh',
                is_default=True
            )
            self.stdout.write(self.style.SUCCESS("Created Demo Customer: customer@nithome.com / customer123"))

        # 2. Categories
        categories_data = [
            {'name': 'GPU', 'slug': 'gpu', 'description': 'High-performance graphics cards for 4K gaming, AI inference, and ray tracing.'},
            {'name': 'CPU', 'slug': 'cpu', 'description': 'Next-gen flagship processors from AMD and Intel for enthusiast workstations.'},
            {'name': 'SSD', 'slug': 'ssd', 'description': 'Ultra-fast PCIe Gen4 & Gen5 NVMe solid state storage drives.'},
            {'name': 'RAM', 'slug': 'ram', 'description': 'High-speed DDR5 & DDR4 desktop memory modules with extreme overclocking support.'},
        ]

        cat_objs = {}
        for cat in categories_data:
            obj, _ = Category.objects.get_or_create(
                slug=cat['slug'],
                defaults={'name': cat['name'], 'description': cat['description']}
            )
            cat_objs[cat['slug']] = obj

        # 3. 10 PC Hardware Products Data
        products_data = [
            # 1. RTX 4090
            {
                'name': 'NVIDIA GeForce RTX 4090 24GB Founders Edition',
                'slug': 'nvidia-geforce-rtx-4090-24gb-founders-edition',
                'category': cat_objs['gpu'],
                'brand': 'NVIDIA',
                'price': Decimal('1699.99'),
                'original_price': Decimal('1899.99'),
                'stock_qty': 8,
                'short_description': 'The ultimate Ada Lovelace GPU with 24GB G6X memory, DLSS 3 frame generation, and extreme 4K ray tracing performance.',
                'long_description': (
                    'The NVIDIA® GeForce RTX™ 4090 is the apex of modern desktop gaming and creative computing. '
                    'Powered by the ultra-efficient NVIDIA Ada Lovelace architecture, it delivers a monumental leap in performance, '
                    'efficiency, and AI-powered graphics. Experience ultra-high performance gaming with immersive ray tracing, '
                    'new streaming multiprocessors, 4th Generation Tensor Cores, and 3rd Generation RT Cores. '
                    'Featuring 24GB of blistering 21 Gbps GDDR6X VRAM, it crunches through 8K rendering, machine learning workflows, '
                    'and competitive gaming with effortless thermal headroom.'
                ),
                'thumbnail_url': 'https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=1000&auto=format&fit=crop&q=80',
                'video_url': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
                'is_featured': True,
                'warranty': '3 Years Manufacturer Warranty',
                'rating': Decimal('5.0'),
                'review_count': 128,
                'images': [
                    ('https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=1600&auto=format&fit=crop&q=90', 'Front View Dual-Flow Heatsink', 1),
                    ('https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=1600&auto=format&fit=crop&q=90', 'PCIe 4.0 Interface & Vapor Chamber Backplate', 2),
                    ('https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=1600&auto=format&fit=crop&q=90', 'Illuminated Titanium Shroud Close-up', 3),
                ],
                'specs': [
                    ('Performance', 'CUDA Cores', '16,384'),
                    ('Performance', 'Boost Clock', '2.52 GHz'),
                    ('Memory', 'VRAM Capacity', '24 GB GDDR6X'),
                    ('Memory', 'Memory Interface', '384-bit (1,008 GB/s bandwidth)'),
                    ('Power & Thermals', 'TDP / Recommended PSU', '450W / 850W Minimum'),
                    ('Connectivity', 'Display Outputs', '3x DisplayPort 1.4a, 1x HDMI 2.1a'),
                ]
            },
            # 2. RTX 4080 Super
            {
                'name': 'ASUS ROG Strix GeForce RTX 4080 Super 16GB OC Edition',
                'slug': 'asus-rog-strix-geforce-rtx-4080-super-16gb-oc',
                'category': cat_objs['gpu'],
                'brand': 'ASUS',
                'price': Decimal('1099.99'),
                'original_price': Decimal('1199.99'),
                'stock_qty': 12,
                'short_description': 'Massive 3.5-slot axial-tech cooling with diecast shroud, dual BIOS, and precision factory overclocking.',
                'long_description': (
                    'The ASUS ROG Strix GeForce RTX™ 4080 SUPER 16GB brings thermal supremacy to high-framerate 4K gaming. '
                    'Featuring larger Axial-tech fans spinning on dual-ball bearings that propel 23% more air through the card, '
                    'patented vapor chamber with milled heatspreader, and massive 3.5-slot heatsink fin array. '
                    'Constructed with auto-extreme automated manufacturing and reinforced metal frame with ARGB Aura Sync lighting.'
                ),
                'thumbnail_url': 'https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=1000&auto=format&fit=crop&q=80',
                'video_url': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4',
                'is_featured': True,
                'warranty': '3 Years Official ROG Warranty',
                'rating': Decimal('4.9'),
                'review_count': 74,
                'images': [
                    ('https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=1600&auto=format&fit=crop&q=90', 'Triple Axial-Tech Fans & RGB Rim', 1),
                    ('https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=1600&auto=format&fit=crop&q=90', 'Vented Exoskeleton Backplate', 2),
                    ('https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=1600&auto=format&fit=crop&q=90', 'Aura Sync Addressable RGB Lighting', 3),
                ],
                'specs': [
                    ('Performance', 'CUDA Cores', '10,240'),
                    ('Performance', 'OC Mode Clock', '2670 MHz'),
                    ('Memory', 'VRAM Capacity', '16 GB GDDR6X'),
                    ('Memory', 'Memory Speed', '23 Gbps'),
                    ('Form Factor', 'Dimensions & Slots', '357.6 x 149.3 x 70.1 mm (3.5 Slot)'),
                    ('Power', 'Power Connectors', '1x 16-pin (12VHPWR)'),
                ]
            },
            # 3. RX 7900 XTX
            {
                'name': 'Sapphire Nitro+ AMD Radeon RX 7900 XTX 24GB Vapor-X',
                'slug': 'sapphire-nitro-amd-radeon-rx-7900-xtx-24gb',
                'category': cat_objs['gpu'],
                'brand': 'Sapphire',
                'price': Decimal('979.99'),
                'original_price': Decimal('1049.99'),
                'stock_qty': 10,
                'short_description': 'RDNA 3 chiplet GPU architecture with 24GB GDDR6, full-length ARGB lightbar, and Vapor-X chamber cooling.',
                'long_description': (
                    'The Sapphire NITRO+ AMD Radeon™ RX 7900 XTX Vapor-X Graphics Card features pioneering AMD RDNA™ 3 chiplet architecture. '
                    'Equipped with 96 compute units, 96 Ray Accelerators, 24GB of ultra-fast GDDR6 memory, and 2nd generation AMD Infinity Cache. '
                    'The iconic Vapor-X Cooling system uses a surface-mounted vapor chamber and composite heatpipes to ensure silent operating temps.'
                ),
                'thumbnail_url': 'https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=1000&auto=format&fit=crop&q=80',
                'video_url': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4',
                'is_featured': False,
                'warranty': '2 Years Sapphire Warranty',
                'rating': Decimal('4.8'),
                'review_count': 56,
                'images': [
                    ('https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=1600&auto=format&fit=crop&q=90', 'Front Shroud with Dual Lightbar', 1),
                    ('https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=1600&auto=format&fit=crop&q=90', 'Die-Cast Aluminum-Magnesium Alloy Frame', 2),
                    ('https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=1600&auto=format&fit=crop&q=90', 'Vapor-X Direct Contact Baseplate', 3),
                ],
                'specs': [
                    ('Performance', 'Stream Processors', '6,144 Units'),
                    ('Performance', 'Boost Clock', '2680 MHz'),
                    ('Memory', 'VRAM', '24 GB GDDR6 / 384-bit'),
                    ('Cache', 'AMD Infinity Cache', '96 MB'),
                    ('Display', 'Outputs', '2x HDMI 2.1a, 2x DisplayPort 2.1 (UHBR13.5)'),
                ]
            },
            # 4. Intel Core i9-14900K
            {
                'name': 'Intel Core i9-14900K 24-Core 6.0GHz Raptor Lake Refresh',
                'slug': 'intel-core-i9-14900k-24-core-processor',
                'category': cat_objs['cpu'],
                'brand': 'Intel',
                'price': Decimal('549.99'),
                'original_price': Decimal('589.99'),
                'stock_qty': 15,
                'short_description': '24 cores (8 P-cores + 16 E-cores) reaching up to 6.0 GHz Intel Thermal Velocity Boost for extreme multitasking.',
                'long_description': (
                    'Take gaming and content creation to uncharted heights with the Intel® Core™ i9-14900K desktop processor. '
                    'Featuring Intel Performance Hybrid Architecture with 8 Performance-cores and 16 Efficient-cores delivering 32 threads. '
                    'Reaches up to 6.0 GHz max turbo frequency out of the box. Fully unlocked for overclocking with support for both DDR5-5600 '
                    'and DDR4 memory, PCIe 5.0 lanes, and Intel Application Optimization (APO) for maximum frame rates in modern titles.'
                ),
                'thumbnail_url': 'https://images.unsplash.com/photo-1555680202-c86f0e12f086?w=1000&auto=format&fit=crop&q=80',
                'video_url': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyBlazes.mp4',
                'is_featured': True,
                'warranty': '3 Years Boxed Intel Warranty',
                'rating': Decimal('4.9'),
                'review_count': 92,
                'images': [
                    ('https://images.unsplash.com/photo-1555680202-c86f0e12f086?w=1600&auto=format&fit=crop&q=90', 'LGA1700 Integrated Heat Spreader', 1),
                    ('https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=1600&auto=format&fit=crop&q=90', 'Gold Substrate Pins Array', 2),
                    ('https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=1600&auto=format&fit=crop&q=90', 'Intel Special Collector Packaging Box', 3),
                ],
                'specs': [
                    ('Core Architecture', 'Total Cores / Threads', '24 Cores (8P + 16E) / 32 Threads'),
                    ('Clock Frequencies', 'Max Turbo / Base P-Core', '6.0 GHz Turbo / 3.2 GHz Base'),
                    ('Cache', 'Intel Smart Cache (L3)', '36 MB'),
                    ('Socket', 'Motherboard Compatibility', 'LGA1700 (Intel 600/700 Series Chipsets)'),
                    ('Power', 'Base / Max Turbo Power', '125W / 253W'),
                ]
            },
            # 5. AMD Ryzen 7 7800X3D
            {
                'name': 'AMD Ryzen 7 7800X3D 8-Core 3D V-Cache Gaming Processor',
                'slug': 'amd-ryzen-7-7800x3d-gaming-processor',
                'category': cat_objs['cpu'],
                'brand': 'AMD',
                'price': Decimal('449.99'),
                'original_price': Decimal('499.99'),
                'stock_qty': 20,
                'short_description': 'The undisputed king of gaming CPUs with 104MB Total Cache, Zen 4 5nm architecture, and 120W TDP efficiency.',
                'long_description': (
                    'The AMD Ryzen™ 7 7800X3D is engineered specifically for world-class gaming performance. '
                    'Equipped with 2nd generation AMD 3D V-Cache™ technology stacked directly onto the 8-core Zen 4 compute die, '
                    'providing a massive 96MB of L3 cache for unmatched low latency and 1% low frame rate consistency in competitive esports '
                    'and open-world simulations. Operates on the long-lived AM5 platform with full support for DDR5 and PCIe 5.0.'
                ),
                'thumbnail_url': 'https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=1000&auto=format&fit=crop&q=80',
                'video_url': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4',
                'is_featured': True,
                'warranty': '3 Years AMD Boxed Warranty',
                'rating': Decimal('5.0'),
                'review_count': 142,
                'images': [
                    ('https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=1600&auto=format&fit=crop&q=90', 'Zen 4 Octa-Core Die with 3D V-Cache', 1),
                    ('https://images.unsplash.com/photo-1555680202-c86f0e12f086?w=1600&auto=format&fit=crop&q=90', 'AM5 Land Grid Array (LGA1718)', 2),
                    ('https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=1600&auto=format&fit=crop&q=90', 'Retail Box with Hologram Security Label', 3),
                ],
                'specs': [
                    ('Architecture', 'Cores / Threads', '8 Cores / 16 Threads (Zen 4 5nm)'),
                    ('Clock Speed', 'Max Boost / Base Clock', '5.0 GHz / 4.2 GHz'),
                    ('Cache', 'Total L2 + L3 Cache', '104 MB (96MB L3 3D V-Cache)'),
                    ('Platform', 'Socket', 'AM5 (AMD B650 / X670 / X870)'),
                    ('Power Efficiency', 'Default TDP', '120W'),
                ]
            },
            # 6. AMD Ryzen 9 7950X
            {
                'name': 'AMD Ryzen 9 7950X 16-Core 32-Thread 5.7GHz Processor',
                'slug': 'amd-ryzen-9-7950x-16-core-processor',
                'category': cat_objs['cpu'],
                'brand': 'AMD',
                'price': Decimal('529.99'),
                'original_price': Decimal('599.99'),
                'stock_qty': 11,
                'short_description': '16 high-performance Zen 4 cores with 5.7GHz boost clock for massive video rendering, 3D compilation, and productivity.',
                'long_description': (
                    'Dominate heavy 3D rendering, software compilation, and 8K video production with the 16-core AMD Ryzen™ 9 7950X. '
                    'Featuring dual Zen 4 CCDs built on TSMC 5nm lithography, 80MB total cache, and 16 cores capable of turbo speeds up to 5.7 GHz. '
                    'Integrated AMD Radeon graphics and Precision Boost Overdrive 2 curve optimizer make it the pinnacle workstation workhorse.'
                ),
                'thumbnail_url': 'https://images.unsplash.com/photo-1555680202-c86f0e12f086?w=1000&auto=format&fit=crop&q=80',
                'video_url': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
                'is_featured': False,
                'warranty': '3 Years AMD Boxed Warranty',
                'rating': Decimal('4.8'),
                'review_count': 63,
                'images': [
                    ('https://images.unsplash.com/photo-1555680202-c86f0e12f086?w=1600&auto=format&fit=crop&q=90', 'AM5 Heatspreader Design', 1),
                    ('https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=1600&auto=format&fit=crop&q=90', 'Motherboard Mounted AM5 Socket View', 2),
                    ('https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=1600&auto=format&fit=crop&q=90', 'Official Retail Packaging', 3),
                ],
                'specs': [
                    ('Compute Cores', 'Cores / Threads', '16 Cores / 32 Threads'),
                    ('Frequency', 'Max Boost Clock', '5.7 GHz'),
                    ('Cache', 'Total L3 Cache', '64 MB'),
                    ('Socket', 'Platform Compatibility', 'AM5 DDR5-only'),
                    ('Thermal', 'Default TDP', '170W (230W PPT)'),
                ]
            },
            # 7. Samsung 990 PRO 2TB SSD
            {
                'name': 'Samsung 990 PRO 2TB PCIe 4.0 NVMe M.2 SSD with Heatsink',
                'slug': 'samsung-990-pro-2tb-pcie-4-nvme-ssd-heatsink',
                'category': cat_objs['ssd'],
                'brand': 'Samsung',
                'price': Decimal('179.99'),
                'original_price': Decimal('219.99'),
                'stock_qty': 25,
                'short_description': 'Sequential read speeds up to 7,450 MB/s, RGB slim heatsink, and Samsung Magician software optimization.',
                'long_description': (
                    'Reach maximum PCIe® 4.0 performance with the Samsung 990 PRO with Heatsink. '
                    'Featuring Samsung\'s custom in-house controller and V-NAND TLC technology, it delivers sequential read speeds '
                    'up to 7,450 MB/s and write speeds up to 6,900 MB/s. The integrated futuristic heatsink maintains optimal operating '
                    'temperatures during extended heavy gaming sessions and PS5 console installation, preventing thermal throttling.'
                ),
                'thumbnail_url': 'https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?w=1000&auto=format&fit=crop&q=80',
                'video_url': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WeAreGoingOnBullrun.mp4',
                'is_featured': True,
                'warranty': '5 Years Limited Samsung Warranty / 1200 TBW',
                'rating': Decimal('4.9'),
                'review_count': 110,
                'images': [
                    ('https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?w=1600&auto=format&fit=crop&q=90', 'Low-Profile Slim Heatsink with RGB LED', 1),
                    ('https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=1600&auto=format&fit=crop&q=90', 'M.2 2280 Form Factor Gold Edge Contacts', 2),
                    ('https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=1600&auto=format&fit=crop&q=90', 'Samsung Magician Verified Security Shield', 3),
                ],
                'specs': [
                    ('Speed', 'Sequential Read / Write', '7,450 MB/s / 6,900 MB/s'),
                    ('IOPS', 'Random Read / Write (4KB)', '1,400K IOPS / 1,550K IOPS'),
                    ('Interface', 'Protocol', 'PCIe Gen 4.0 x4, NVMe 2.0'),
                    ('Form Factor', 'Dimensions', 'M.2 2280 with Heatsink (PS5 Compatible)'),
                    ('Durability', 'Endurance (TBW)', '1,200 TBW'),
                ]
            },
            # 8. Crucial T700 2TB Gen5 SSD
            {
                'name': 'Crucial T700 2TB PCIe Gen5 NVMe M.2 SSD (12,400 MB/s)',
                'slug': 'crucial-t700-2tb-pcie-gen5-nvme-ssd',
                'category': cat_objs['ssd'],
                'brand': 'Crucial',
                'price': Decimal('279.99'),
                'original_price': Decimal('329.99'),
                'stock_qty': 14,
                'short_description': 'Blistering Gen5 speed up to 12,400 MB/s with premium aluminum and nickel-plated copper passive heatsink.',
                'long_description': (
                    'Experience generational speed with the Crucial T700 PCIe® 5.0 NVMe® SSD. '
                    'Harnessing Micron® 232-layer 3D TLC NAND and the Phison PS5026-E26 controller, the T700 reaches sequential speeds '
                    'of up to 12,400 MB/s read and 11,800 MB/s write. Near-instant game asset streaming with Microsoft DirectStorage support '
                    'and an extruded aluminum heatsink engineered to dissipate heat without noisy active fans.'
                ),
                'thumbnail_url': 'https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?w=1000&auto=format&fit=crop&q=80',
                'video_url': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4',
                'is_featured': False,
                'warranty': '5 Years Crucial Micron Warranty',
                'rating': Decimal('4.8'),
                'review_count': 39,
                'images': [
                    ('https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?w=1600&auto=format&fit=crop&q=90', 'Passive Copper-Core Heatsink Fins', 1),
                    ('https://images.unsplash.com/photo-1555680202-c86f0e12f086?w=1600&auto=format&fit=crop&q=90', 'Micron 232-Layer TLC NAND Flash View', 2),
                    ('https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=1600&auto=format&fit=crop&q=90', 'PCIe 5.0 x4 High Bandwidth Bus Interface', 3),
                ],
                'specs': [
                    ('Interface', 'PCIe Standard', 'PCIe Gen 5.0 x4 NVMe 2.0'),
                    ('Throughput', 'Seq Read / Seq Write', '12,400 MB/s / 11,800 MB/s'),
                    ('Random 4K IOPS', 'Read / Write', '1,500,000 IOPS / 1,500,000 IOPS'),
                    ('Technology', 'NAND Flash', 'Micron 232-Layer 3D TLC'),
                    ('Endurance', 'TBW Rating', '1,200 Terabytes Written'),
                ]
            },
            # 9. Corsair Vengeance RGB DDR5 32GB
            {
                'name': 'Corsair Vengeance RGB DDR5 32GB (2x16GB) 6000MHz CL30',
                'slug': 'corsair-vengeance-rgb-ddr5-32gb-6000mhz-cl30',
                'category': cat_objs['ram'],
                'brand': 'Corsair',
                'price': Decimal('124.99'),
                'original_price': Decimal('149.99'),
                'stock_qty': 30,
                'short_description': 'Optimized for Intel XMP 3.0 & AMD EXPO with tight CL30-36-36-76 timings, dynamic ten-zone RGB lighting, and onboard voltage regulation.',
                'long_description': (
                    'Elevate your PC build aesthetic and gaming frame rates with CORSAIR VENGEANCE RGB DDR5 memory. '
                    'Delivering 6000MT/s frequency with low CL30 latency, custom performance PCB for extreme signal quality, '
                    'and hand-sorted memory chips. Ten individual, ultra-bright RGB LEDs per module encased in a panoramic light bar '
                    'deliver radiant ambient illumination synchronized through Corsair iCUE.'
                ),
                'thumbnail_url': 'https://images.unsplash.com/photo-1562976540-1502c2145186?w=1000&auto=format&fit=crop&q=80',
                'video_url': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4',
                'is_featured': True,
                'warranty': 'Lifetime Limited Manufacturer Warranty',
                'rating': Decimal('4.9'),
                'review_count': 95,
                'images': [
                    ('https://images.unsplash.com/photo-1562976540-1502c2145186?w=1600&auto=format&fit=crop&q=90', 'Dual Channel Matched Pair with ARGB Diffuser', 1),
                    ('https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=1600&auto=format&fit=crop&q=90', 'Solid Aluminum Anodized Heatspreader', 2),
                    ('https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=1600&auto=format&fit=crop&q=90', 'Onboard Power Management IC (PMIC)', 3),
                ],
                'specs': [
                    ('Kit Capacity', 'Configuration', '32GB (2x 16GB Dual Channel)'),
                    ('Speed & Timings', 'Tested Speed / Latency', 'DDR5 6000MT/s / CL30-36-36-76'),
                    ('Voltage', 'Tested Voltage', '1.40V (Onboard PMIC)'),
                    ('Profile Support', 'Overclocking Standards', 'Intel XMP 3.0 & AMD EXPO Dual Profile'),
                    ('Lighting', 'RGB Control', '10-Zone Addressable RGB (iCUE Compatible)'),
                ]
            },
            # 10. G.Skill Trident Z5 Neo RGB 64GB
            {
                'name': 'G.Skill Trident Z5 Neo RGB 64GB (2x32GB) DDR5 6000MHz CL30 EXPO',
                'slug': 'gskill-trident-z5-neo-rgb-64gb-ddr5-6000mhz',
                'category': cat_objs['ram'],
                'brand': 'G.Skill',
                'price': Decimal('219.99'),
                'original_price': Decimal('249.99'),
                'stock_qty': 18,
                'short_description': 'High-capacity 64GB dual-channel DDR5 kit specifically tuned for AMD AM5 Ryzen 7000/9000 systems with matte black finish.',
                'long_description': (
                    'Trident Z5 Neo RGB series DDR5 memory is engineered for ultra-high overclocked performance on AMD AM5 platforms. '
                    'Featuring AMD EXPO (EXtended Profiles for Overclocking) technology for effortless memory overclocking in supported BIOS. '
                    'Featuring a sleek matte black aluminum body paired with a crystalline translucent RGB light bar, '
                    'the Trident Z5 Neo RGB is the ideal choice for gamers, overclockers, content creators, and PC enthusiasts.'
                ),
                'thumbnail_url': 'https://images.unsplash.com/photo-1562976540-1502c2145186?w=1000&auto=format&fit=crop&q=80',
                'video_url': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
                'is_featured': False,
                'warranty': 'Lifetime Limited G.Skill Warranty',
                'rating': Decimal('5.0'),
                'review_count': 68,
                'images': [
                    ('https://images.unsplash.com/photo-1562976540-1502c2145186?w=1600&auto=format&fit=crop&q=90', 'Trident Z5 Hypercar-Inspired Matte Black Heatspreader', 1),
                    ('https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=1600&auto=format&fit=crop&q=90', 'Crystalline Lightbar with Smooth Gradient Diffusion', 2),
                    ('https://images.unsplash.com/photo-1555680202-c86f0e12f086?w=1600&auto=format&fit=crop&q=90', 'High-Layer Density Precision Signal PCB', 3),
                ],
                'specs': [
                    ('Capacity', 'Kit Details', '64GB (2x 32GB High Density)'),
                    ('Speed Rating', 'Frequency / CAS Latency', 'DDR5 6000 MHz / CL30-40-40-96'),
                    ('Voltage', 'Profile Voltage', '1.40V'),
                    ('Optimization', 'Overclock Profile', 'AMD EXPO Certified'),
                    ('Form Factor', 'Module Height', '44 mm (Unbuffered Non-ECC)'),
                ]
            },
        ]

        for pdata in products_data:
            images = pdata.pop('images')
            specs = pdata.pop('specs')
            product, created = Product.objects.update_or_create(
                slug=pdata['slug'],
                defaults=pdata
            )
            # Remove old images & specs if re-running
            product.images.all().delete()
            product.specifications.all().delete()

            for img_url, caption, order in images:
                ProductImage.objects.create(
                    product=product,
                    image_url=img_url,
                    caption=caption,
                    is_4k=True,
                    order=order
                )

            for group, spec_name, spec_value in specs:
                ProductSpecification.objects.create(
                    product=product,
                    group=group,
                    spec_name=spec_name,
                    spec_value=spec_value
                )

            status_str = "Created" if created else "Updated"
            self.stdout.write(f"  - [{status_str}] {product.name}")

        self.stdout.write(self.style.SUCCESS("All 10 PC Hardware products and accounts seeded successfully!"))

"""Hand-written SEO landing content for developer pages (/developers/<slug>/).

developer_detail.html renders a generic page for every developer. When a
developer has an entry here, the template adds these sections around the
listing grid, server-rendered so search engines can read them.

Strings marked with mark_safe() contain internal links and are trusted
(they live in this file, never in user input). To add a developer, copy the
Nakheel entry, change the key to the lower-cased developer name, and list any
other spellings of the name in ALIASES.
"""
import json

from django.utils.safestring import mark_safe

DEVELOPER_CONTENT = {
    'nakheel': {
        'meta_title': 'Nakheel Properties for Sale in Dubai | KIF Realty',
        'meta_description': (
            'See Nakheel properties in Dubai: Bay Grove Residences, Palm Central, '
            'Palm Jebel Ali plots and more. Get prices and advice from '
            'RERA-certified KIF Realty.'
        ),
        'logo_alt': 'Nakheel logo',

        # Section 1: Hero
        'h1': 'Nakheel Properties in Dubai',
        'tagline': 'Iconic Destinations. Exceptional Homes. Inspired Living.',
        'intro': (
            'Browse Nakheel properties for sale in Dubai: waterfront apartments, '
            'villas and plots across Dubai Islands, Palm Jebel Ali and Mohammed '
            'Bin Rashid City. Get project details and personal guidance from the '
            'RERA-certified advisors at KIF Realty.'
        ),
        # Stats bar; the property count stays live from the listings.
        'stats': {
            'price': 'On Request',
            'communities': 3,
            'types': 3,
        },

        # Section 2: About
        'about_heading': "About Nakheel: One of Dubai's Leading Developers",
        'about': [
            'Nakheel is a Dubai master developer best known for waterfront and '
            'island communities, including Palm Jumeirah, Palm Jebel Ali and '
            'Dubai Islands. Its portfolio also includes established '
            'neighbourhoods such as Jumeirah Islands, Jumeirah Park and '
            'International City.',
            'Buyers look to Nakheel for large, master-planned communities with '
            'beaches, parks and leisure close to home. On this page you can '
            'browse the Nakheel projects currently available through KIF '
            'Realty, from beachfront apartments at Bay Grove Residences to '
            'villas and plots on Palm Jebel Ali.',
            mark_safe(
                'KIF Realty is a licensed, RERA-certified Dubai brokerage. We help '
                'you compare Nakheel projects, check what is available right now '
                'and understand the next steps, whether you are buying a home to '
                'live in or a property to invest in. You can also compare '
                '<a href="/developers/">all Dubai developers</a>.'
            ),
        ],

        # Section 3: Communities
        'communities_heading': 'Nakheel Communities in Dubai',
        'communities_intro': (
            'Our current Nakheel listings sit in three destinations. Here is '
            'what each one offers.'
        ),
        'communities': [
            {
                'name': 'Dubai Islands',
                'kind': 'Beachfront apartments',
                'icon': 'bi-water',
                'text': (
                    'A waterfront island destination off the Deira coast, built '
                    'around beaches, marinas and leisure spaces. Nakheel projects '
                    'here include Bay Grove Residences (several phases), Beach '
                    'Residences and Bay Residences.'
                ),
            },
            {
                'name': 'Palm Jebel Ali',
                'kind': 'Villas, plots and resort-style homes',
                'icon': 'bi-tree',
                'text': (
                    'A palm-shaped island development near Jebel Ali, planned '
                    'with beachfront villas and residential buildings between its '
                    'fronds. Projects here include Palm Central Private '
                    'Residences, Palm Jebel Ali plots and the Fronds K to P villas '
                    '(sold out).'
                ),
            },
            {
                'name': 'Mohammed Bin Rashid City',
                'kind': 'Lagoon-facing villas',
                'icon': 'bi-house-heart',
                'text': (
                    'District One West brings large villas and mansions set '
                    'around crystal lagoons in Mohammed Bin Rashid City. The '
                    'project is sold out, so ask us about resale options and '
                    'similar communities.'
                ),
            },
        ],

        # Section 4: Above the listing grid
        'listings_heading': 'Nakheel Properties for Sale in Dubai',
        'listings_intro': (
            'Every listing below is a Nakheel project we can help you with. Tags '
            'show whether a project is pre-launch, resale or sold out. Prices '
            'change with each launch phase, so they are shown on request. Tap '
            'any project, or speak to an advisor for the latest price list and '
            'payment plan.'
        ),

        # Section 5: Why KIF Realty
        'why_heading': 'Why Buy Nakheel Properties with KIF Realty?',
        'why_intro': (
            'Your property journey deserves personal attention and trusted '
            'guidance. We make it easier to discover and compare Nakheel '
            'developments across Dubai.'
        ),
        'why_points': [
            {
                'title': 'Curated Property Options',
                'icon': 'bi-grid-1x2',
                'text': (
                    'We show the Nakheel projects we can actually offer, with the '
                    'status of each one stated clearly: pre-launch, resale or '
                    'sold out.'
                ),
            },
            {
                'title': 'Expert Property Guidance',
                'icon': 'bi-compass',
                'text': (
                    'Our real estate advisors explain locations, unit types, '
                    'payment plans and handover timelines in plain language.'
                ),
            },
            {
                'title': 'Personalised Assistance',
                'icon': 'bi-person-check',
                'text': (
                    'Tell us your budget, your preferred community and whether '
                    'you are buying to live in or to invest. We match options '
                    'to you.'
                ),
            },
            {
                'title': 'A Smooth Property Journey',
                'icon': 'bi-signpost-split',
                'text': (
                    'From shortlisting to booking and the paperwork that follows, '
                    'our team stays with you at every step.'
                ),
            },
        ],
        'trust_line': [
            'Licensed Dubai broker',
            'RERA License No. 45840',
            'Office 807, Al Moosa Tower 1, Sheikh Zayed Road',
        ],

        # Section 6: How to buy
        'steps_heading': 'How to Buy a Nakheel Property in Dubai',
        'steps_intro': 'Buying with KIF Realty follows four simple steps.',
        'steps': [
            {
                'title': 'Tell us what you need',
                'text': (
                    'Share your budget, preferred community and whether the '
                    'purchase is a home or an investment.'
                ),
            },
            {
                'title': 'Receive a shortlist',
                'text': (
                    'We send matching Nakheel projects with unit types, current '
                    'status, price list and payment plan.'
                ),
            },
            {
                'title': 'Reserve your unit',
                'text': (
                    'Choose your unit, sign the reservation form and pay the '
                    'booking deposit.'
                ),
            },
            {
                'title': 'Complete the purchase',
                'text': (
                    'Sign the sales agreement and follow the payment plan. '
                    'Off-plan purchases are typically registered with the Dubai '
                    'Land Department and paid into a regulated escrow account.'
                ),
            },
        ],

        # Section 7: FAQ (also emitted as FAQPage schema)
        'faq_heading': 'Frequently Asked Questions About Nakheel Properties',
        'faqs': [
            {
                'q': 'What is Nakheel known for in Dubai?',
                'a': (
                    'Nakheel is a Dubai master developer known for large '
                    'waterfront and island communities, including Palm Jumeirah, '
                    'Palm Jebel Ali and Dubai Islands. It also developed '
                    'established neighbourhoods such as Jumeirah Islands, '
                    'Jumeirah Park and International City.'
                ),
            },
            {
                'q': 'Which Nakheel properties can I explore with KIF Realty?',
                'a': (
                    'This page lists Nakheel projects such as Bay Grove '
                    'Residences, Beach Residences and Bay Residences on Dubai '
                    'Islands, Palm Central Private Residences and plots on Palm '
                    'Jebel Ali, and District One West. Each listing shows whether '
                    'it is pre-launch, resale or sold out.'
                ),
            },
            {
                'q': 'What types of Nakheel properties are available?',
                'a': (
                    'Depending on the project, Nakheel properties include '
                    'waterfront apartments, villas and residential plots. '
                    'Availability changes with each phase, so ask our advisors '
                    'which unit types are open right now.'
                ),
            },
            {
                'q': 'How much do Nakheel properties cost?',
                'a': (
                    'Prices depend on the project, community, unit type and '
                    'phase, and they change as phases launch and sell out. Prices '
                    'on this page are shown on request. Contact KIF Realty for '
                    'the latest price list and payment plan for the project you '
                    'like.'
                ),
            },
            {
                'q': 'Are Nakheel properties off-plan or ready to move in?',
                'a': (
                    'It depends on the project. Some Nakheel developments are '
                    'off-plan or pre-launch, others are available as resale, and '
                    'some phases are sold out. The status tag on each listing '
                    'shows where it stands, and an advisor can confirm the '
                    'expected handover.'
                ),
            },
            {
                'q': 'Can foreigners buy Nakheel properties in Dubai?',
                'a': (
                    "Foreign nationals can generally buy property in Dubai's "
                    'designated freehold areas. Rules and eligibility can differ '
                    'by project, so our advisors confirm the ownership terms '
                    'before you reserve a unit.'
                ),
            },
            {
                'q': 'How can I explore Nakheel properties with KIF Realty?',
                'a': (
                    'Use the Speak to an Advisor button or email '
                    'info@kifrealty.com. Tell us your budget, preferred community '
                    'and purpose, and our RERA-certified team will share a '
                    'shortlist, project details and the next steps. We are '
                    'available Sunday to Thursday 9AM to 7PM and Saturday 10AM '
                    'to 4PM.'
                ),
            },
        ],

        # Internal links shown under the FAQ
        'related_links': [
            ('off-plan properties in Dubai', '/off-plan-residential-properties'),
            ('plots for sale in Dubai', '/plots-for-sale'),
            ('beachfront properties in Dubai', '/beachfront-Properties'),
            ('mortgage calculator', '/?scroll=mortgage-calculator'),
            ('speak to an advisor', '/contact/'),
        ],

        # Section 8: Final call to action
        'cta_heading': 'Find Your Nakheel Property with KIF Realty',
        'cta_tagline': 'Your Next Chapter Begins Here.',
        'cta_text': (
            'Whether you are searching for a waterfront apartment, a spacious '
            'family villa or a plot on Palm Jebel Ali, KIF Realty is here to '
            "guide you. Explore Nakheel's developments and take the next step "
            'towards a place to call home.'
        ),
    },
}

# Other spellings of a developer name -> key in DEVELOPER_CONTENT
ALIASES = {
    'nakheel properties': 'nakheel',
    'nakheel pjsc': 'nakheel',
}


def get_developer_content(name):
    """Landing content for a developer name, or None."""
    key = ' '.join((name or '').lower().split())
    return DEVELOPER_CONTENT.get(ALIASES.get(key, key))


def faq_schema_json(content):
    """FAQPage JSON-LD for the content's FAQs, safe to embed in a <script>."""
    data = {
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        'mainEntity': [
            {
                '@type': 'Question',
                'name': f['q'],
                'acceptedAnswer': {'@type': 'Answer', 'text': f['a']},
            }
            for f in content['faqs']
        ],
    }
    # Escape '<' so the JSON can never close the surrounding <script> tag.
    return mark_safe(json.dumps(data, ensure_ascii=False).replace('<', '\\u003c'))

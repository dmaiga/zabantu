from django.db import migrations

INITIAL = [('+223 77 94 14 70', 1), ('+223 76 63 45 15', 2)]


def add_numbers(apps, schema_editor):
    DonationNumber = apps.get_model('site_web', 'DonationNumber')
    if not DonationNumber.objects.exists():
        for number, order in INITIAL:
            DonationNumber.objects.create(number=number, operator='Orange Money', order=order)


class Migration(migrations.Migration):
    dependencies = [('site_web', '0012_donationnumber')]
    operations = [migrations.RunPython(add_numbers, migrations.RunPython.noop)]

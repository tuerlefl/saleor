from django.conf import settings
from fedex.services.rates import RateService
from fedex.config import FedexConfiguration
from prices import Price

from ..fedex import FEDEX_CREDENTIALS, FEDEX_CONFIG


class BaseCourier(object):

    def get_service(self, **kwargs):
        return NotImplemented

    def get_shipment(self, **kwargs):
        return NotImplemented

    def get_cost(self, **kwargs):
        return NotImplemented


class Courier(BaseCourier):

    def __init__(self, group):
        self.group = group
        self.service = self.get_service()

    def get_service(self, **kwargs):
        config = FedexConfiguration(
            key=FEDEX_CREDENTIALS.get('key'),
            password=FEDEX_CREDENTIALS.get('password'),
            account_number=FEDEX_CREDENTIALS.get('account_number'),
            meter_number=FEDEX_CREDENTIALS.get('meter_number'),
            wsdls=FEDEX_CREDENTIALS.get('wsdls'))

        return RateService(configuration=config)

    def get_weight(self):
        return sum(line.product.weight for line in self.group)

    def get_shipment(self):
        package = self.service.create_package()
        package.GroupPackageCount = 1
        package.PhysicalPackaging = "BOX"
        package.Weight.Value = self.get_weight()
        package.Weight.Units = FEDEX_CONFIG.get('package_units')

        shipment = self.service.create_shipment()
        shipment.DropoffType = "REGULAR_PICKUP"
        shipment.ServiceType = "FEDEX_GROUND"
        shipment.PackagingType = "YOUR_PACKAGING"
        shipment.EdtRequestType = 'NONE'
        shipment.Shipper.Address.PostalCode = \
            FEDEX_CONFIG.get('shipper_postal_code')
        shipment.Shipper.Address.CountryCode = \
            FEDEX_CONFIG.get('shipper_country_code')
        shipment.Shipper.Address.Residential = False
        shipment.Recipient.Address.PostalCode = \
            FEDEX_CONFIG.get('recipient_postal_code')
        shipment.Recipient.Address.CountryCode = \
            FEDEX_CONFIG.get('recipient_country_code')
        shipment.RateRequestTypes = ["ACCOUNT"]
        shipment.ShippingChargesPayment.PaymentType = "SENDER"
        shipment.RequestedPackageLineItems.append(package)
        shipment.PackageCount = len(shipment.RequestedPackageLineItems)

        return shipment

    def get_cost(self):
        response = self.service.get_rates(shipment=self.get_shipment())
        print response
        cost = 0

        if not response.HighestSeverity in ['SUCCESS']:
            return Price(0, currency=settings.SATCHLESS_DEFAULT_CURRENCY)

        for rate_detail in response.RateReplyDetails[0].RatedShipmentDetails:
            amount = rate_detail.ShipmentRateDetail.TotalNetFedExCharge.Amount
            cost = max(cost, amount)
        return Price(cost, currency=settings.SATCHLESS_DEFAULT_CURRENCY)

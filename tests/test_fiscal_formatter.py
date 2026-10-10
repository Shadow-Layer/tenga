"""Tests for Fiscal Submission Request Formatting (T2)."""
import pytest
from decimal import Decimal
from datetime import datetime
from src.services.fiscal_formatter import (
    FiscalFormatter, FiscalSubmissionRequest, FiscalLineItem,
    PaymentMethod
)


class TestFiscalLineItem:
    """Test fiscal line item validation."""
    
    def test_valid_line_item(self):
        """Test valid line item creation."""
        item = FiscalLineItem(
            product_name="Test Product",
            quantity=Decimal("2.00"),
            unit_price=Decimal("50.0000"),
            total_price=Decimal("100.0000"),
            tax_rate=Decimal("15.00"),
            tax_amount=Decimal("15.0000")
        )
        assert item.product_name == "Test Product"
        assert item.quantity == Decimal("2.00")
    
    def test_line_item_product_name_required(self):
        """Test product name is required."""
        with pytest.raises(ValueError):
            FiscalLineItem(
                product_name="",
                quantity=Decimal("1.00"),
                unit_price=Decimal("10.0000"),
                total_price=Decimal("10.0000"),
                tax_rate=Decimal("0.00"),
                tax_amount=Decimal("0.0000")
            )
    
    def test_line_item_product_name_max_50_chars(self):
        """Test product name max length is 50 characters."""
        with pytest.raises(ValueError):
            FiscalLineItem(
                product_name="A" * 51,
                quantity=Decimal("1.00"),
                unit_price=Decimal("10.0000"),
                total_price=Decimal("10.0000"),
                tax_rate=Decimal("0.00"),
                tax_amount=Decimal("0.0000")
            )
    
    def test_line_item_quantity_2_decimals(self):
        """Test quantity requires ≤2 decimal places."""
        # Valid
        item = FiscalLineItem(
            product_name="Product",
            quantity=Decimal("1.50"),
            unit_price=Decimal("10.0000"),
            total_price=Decimal("15.0000"),
            tax_rate=Decimal("0.00"),
            tax_amount=Decimal("0.0000")
        )
        assert item.quantity == Decimal("1.50")
        
        # Invalid
        with pytest.raises(ValueError, match="≤2 decimals"):
            FiscalLineItem(
                product_name="Product",
                quantity=Decimal("1.555"),
                unit_price=Decimal("10.0000"),
                total_price=Decimal("15.0000"),
                tax_rate=Decimal("0.00"),
                tax_amount=Decimal("0.0000")
            )
    
    def test_line_item_prices_4_decimals(self):
        """Test prices require ≤4 decimal places."""
        # Valid
        item = FiscalLineItem(
            product_name="Product",
            quantity=Decimal("1.00"),
            unit_price=Decimal("10.1234"),
            total_price=Decimal("10.1234"),
            tax_rate=Decimal("0.00"),
            tax_amount=Decimal("0.0000")
        )
        assert item.unit_price == Decimal("10.1234")
        
        # Invalid
        with pytest.raises(ValueError, match="≤4 decimals"):
            FiscalLineItem(
                product_name="Product",
                quantity=Decimal("1.00"),
                unit_price=Decimal("10.12345"),
                total_price=Decimal("10.1234"),
                tax_rate=Decimal("0.00"),
                tax_amount=Decimal("0.0000")
            )
    
    def test_line_item_negative_quantity_invalid(self):
        """Test negative quantity is rejected."""
        with pytest.raises(ValueError):
            FiscalLineItem(
                product_name="Product",
                quantity=Decimal("-1.00"),
                unit_price=Decimal("10.0000"),
                total_price=Decimal("10.0000"),
                tax_rate=Decimal("0.00"),
                tax_amount=Decimal("0.0000")
            )
    
    def test_line_item_tax_rate_0_to_100(self):
        """Test tax rate must be between 0 and 100."""
        # Valid edge cases
        FiscalLineItem(
            product_name="Product",
            quantity=Decimal("1.00"),
            unit_price=Decimal("10.0000"),
            total_price=Decimal("10.0000"),
            tax_rate=Decimal("0.00"),
            tax_amount=Decimal("0.0000")
        )
        
        FiscalLineItem(
            product_name="Product",
            quantity=Decimal("1.00"),
            unit_price=Decimal("10.0000"),
            total_price=Decimal("10.0000"),
            tax_rate=Decimal("100.00"),
            tax_amount=Decimal("10.0000")
        )
        
        # Invalid
        with pytest.raises(ValueError):
            FiscalLineItem(
                product_name="Product",
                quantity=Decimal("1.00"),
                unit_price=Decimal("10.0000"),
                total_price=Decimal("10.0000"),
                tax_rate=Decimal("150.00"),
                tax_amount=Decimal("10.0000")
            )


class TestFiscalSubmissionRequest:
    """Test fiscal submission request validation."""
    
    def test_valid_submission_request(self):
        """Test valid submission request."""
        timestamp = datetime.utcnow()
        items = [
            {
                "product_name": "Item 1",
                "quantity": Decimal("2.00"),
                "unit_price": Decimal("50.0000"),
                "total_price": Decimal("100.0000"),
                "tax_rate": Decimal("15.00"),
                "tax_amount": Decimal("15.0000")
            }
        ]
        
        request = FiscalSubmissionRequest(
            sale_id="SALE-001",
            device_id="DEV-12345",
            timestamp=timestamp,
            items=[FiscalLineItem(**item) for item in items],
            subtotal=Decimal("100.0000"),
            tax_amount=Decimal("15.0000"),
            total=Decimal("115.0000"),
            payment_method=PaymentMethod.CASH,
            idempotency_key="KEY-001"
        )
        
        assert request.sale_id == "SALE-001"
        assert request.total == Decimal("115.0000")
    
    def test_submission_totals_consistency(self):
        """Test submission validates total consistency."""
        timestamp = datetime.utcnow()
        items = [
            {
                "product_name": "Item 1",
                "quantity": Decimal("2.00"),
                "unit_price": Decimal("50.0000"),
                "total_price": Decimal("100.0000"),
                "tax_rate": Decimal("15.00"),
                "tax_amount": Decimal("15.0000")
            }
        ]
        
        # Valid case
        request = FiscalSubmissionRequest(
            sale_id="SALE-001",
            device_id="DEV-12345",
            timestamp=timestamp,
            items=[FiscalLineItem(**item) for item in items],
            subtotal=Decimal("100.0000"),
            tax_amount=Decimal("15.0000"),
            total=Decimal("115.0000"),
            payment_method=PaymentMethod.CASH,
            idempotency_key="KEY-001"
        )
        assert request.total == Decimal("115.0000")
        
        # Invalid subtotal
        with pytest.raises(ValueError, match="sum of line items"):
            FiscalSubmissionRequest(
                sale_id="SALE-001",
                device_id="DEV-12345",
                timestamp=timestamp,
                items=[FiscalLineItem(**item) for item in items],
                subtotal=Decimal("50.0000"),  # Wrong subtotal
                tax_amount=Decimal("15.0000"),
                total=Decimal("115.0000"),
                payment_method=PaymentMethod.CASH,
                idempotency_key="KEY-001"
            )
    
    def test_submission_total_validation(self):
        """Test total = subtotal + tax validation."""
        timestamp = datetime.utcnow()
        items = [
            {
                "product_name": "Item 1",
                "quantity": Decimal("1.00"),
                "unit_price": Decimal("100.0000"),
                "total_price": Decimal("100.0000"),
                "tax_rate": Decimal("15.00"),
                "tax_amount": Decimal("15.0000")
            }
        ]
        
        # Invalid total
        with pytest.raises(ValueError, match="subtotal .* tax"):
            FiscalSubmissionRequest(
                sale_id="SALE-001",
                device_id="DEV-12345",
                timestamp=timestamp,
                items=[FiscalLineItem(**item) for item in items],
                subtotal=Decimal("100.0000"),
                tax_amount=Decimal("15.0000"),
                total=Decimal("120.0000"),  # Wrong total
                payment_method=PaymentMethod.CASH,
                idempotency_key="KEY-001"
            )
    
    def test_submission_sale_id_required(self):
        """Test sale ID is required."""
        with pytest.raises(ValueError):
            FiscalSubmissionRequest(
                sale_id="",
                device_id="DEV-12345",
                timestamp=datetime.utcnow(),
                items=[],
                subtotal=Decimal("0.0000"),
                tax_amount=Decimal("0.0000"),
                total=Decimal("0.0000"),
                payment_method=PaymentMethod.CASH,
                idempotency_key="KEY-001"
            )


class TestFiscalFormatter:
    """Test fiscal formatter utility."""
    
    def test_format_request_success(self):
        """Test successful request formatting."""
        items = [
            {
                "product_name": "Product 1",
                "quantity": Decimal("2.00"),
                "unit_price": Decimal("50.0000"),
                "total_price": Decimal("100.0000"),
                "tax_rate": Decimal("15.00"),
                "tax_amount": Decimal("15.0000")
            }
        ]
        
        request = FiscalFormatter.format_request(
            sale_id="SALE-001",
            device_id="DEV-12345",
            items=items,
            subtotal=Decimal("100.0000"),
            tax_amount=Decimal("15.0000"),
            total=Decimal("115.0000"),
            payment_method="CASH",
            idempotency_key="KEY-001"
        )
        
        assert request.sale_id == "SALE-001"
        assert request.total == Decimal("115.0000")
    
    def test_format_request_uses_current_timestamp_if_not_provided(self):
        """Test formatter uses current timestamp if not provided."""
        items = [
            {
                "product_name": "Product 1",
                "quantity": Decimal("1.00"),
                "unit_price": Decimal("10.0000"),
                "total_price": Decimal("10.0000"),
                "tax_rate": Decimal("0.00"),
                "tax_amount": Decimal("0.0000")
            }
        ]
        
        before = datetime.utcnow()
        request = FiscalFormatter.format_request(
            sale_id="SALE-001",
            device_id="DEV-12345",
            items=items,
            subtotal=Decimal("10.0000"),
            tax_amount=Decimal("0.0000"),
            total=Decimal("10.0000"),
            payment_method="CASH",
            idempotency_key="KEY-001"
        )
        after = datetime.utcnow()
        
        assert before <= request.timestamp <= after
    
    def test_format_request_invalid_payment_method(self):
        """Test formatter rejects invalid payment method."""
        items = [
            {
                "product_name": "Product 1",
                "quantity": Decimal("1.00"),
                "unit_price": Decimal("10.0000"),
                "total_price": Decimal("10.0000"),
                "tax_rate": Decimal("0.00"),
                "tax_amount": Decimal("0.0000")
            }
        ]
        
        with pytest.raises(ValueError):
            FiscalFormatter.format_request(
                sale_id="SALE-001",
                device_id="DEV-12345",
                items=items,
                subtotal=Decimal("10.0000"),
                tax_amount=Decimal("0.0000"),
                total=Decimal("10.0000"),
                payment_method="INVALID",  # Invalid
                idempotency_key="KEY-001"
            )
    
    def test_to_dict_conversion(self):
        """Test converting request to dictionary."""
        items = [
            {
                "product_name": "Product 1",
                "quantity": Decimal("1.00"),
                "unit_price": Decimal("10.0000"),
                "total_price": Decimal("10.0000"),
                "tax_rate": Decimal("0.00"),
                "tax_amount": Decimal("0.0000")
            }
        ]
        
        request = FiscalFormatter.format_request(
            sale_id="SALE-001",
            device_id="DEV-12345",
            items=items,
            subtotal=Decimal("10.0000"),
            tax_amount=Decimal("0.0000"),
            total=Decimal("10.0000"),
            payment_method="CASH",
            idempotency_key="KEY-001"
        )
        
        result_dict = FiscalFormatter.to_dict(request)
        assert isinstance(result_dict, dict)
        assert result_dict['sale_id'] == "SALE-001"
        assert result_dict['payment_method'] == "CASH"

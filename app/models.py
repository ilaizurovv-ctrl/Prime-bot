import enum
from datetime import datetime, timezone
from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

class DealStatus(str, enum.Enum):
    CREATED = "created"
    WAITING_FOR_BUYER = "waiting_for_buyer"
    AWAITING_PAYMENT = "awaiting_payment"
    FUNDED_TESTNET = "funded_testnet"
    GIFT_TRANSFER_PENDING = "gift_transfer_pending"
    NFT_RECEIVED = "nft_received"
    NFT_VERIFIED = "nft_verified"
    NFT_DELIVERED = "nft_delivered"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"

class NFTKind(str, enum.Enum):
    TELEGRAM_GIFT = "telegram_gift"
    TON_NFT = "ton_nft"

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    balance_ton_nano: Mapped[int] = mapped_column(BigInteger, default=0)
    balance_rub_kopecks: Mapped[int] = mapped_column(BigInteger, default=0)
    balance_stars: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Deal(Base):
    __tablename__ = "deals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    buyer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    amount_nano: Mapped[int] = mapped_column(BigInteger)
    fee_bps: Mapped[int] = mapped_column(Integer, default=150)
    asset: Mapped[str] = mapped_column(String(12), default="TON")
    nft_kind: Mapped[NFTKind | None] = mapped_column(Enum(NFTKind), nullable=True)
    nft_reference: Mapped[str | None] = mapped_column(String(256), nullable=True)
    collection_address: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[DealStatus] = mapped_column(Enum(DealStatus), default=DealStatus.CREATED)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class BalanceTransaction(Base):
    __tablename__ = "balance_transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    currency: Mapped[str] = mapped_column(String(8))
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    action: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str] = mapped_column(String(256), default="")
    admin_telegram_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

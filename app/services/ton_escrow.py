"""Deliberately non-custodial placeholder.

Production TODO:
- integrate a trusted TON indexer/provider with transaction finality checks;
- verify destination wallet, amount, asset, memo/comment, and transaction uniqueness;
- persist observed transaction hashes and reconcile independently;
- use an audited multisig or isolated signer service for releases/refunds;
- implement idempotent release/refund state transitions and dual control.

Never treat a user-supplied transaction hash or screenshot as proof of payment.
Never store seed phrases/private keys in the Telegram bot process.
"""

class TonEscrow:
    async def verify_incoming_payment(self, *args, **kwargs) -> bool:
        raise NotImplementedError("TON payment verification is not enabled in this starter")

    async def release_to_seller(self, *args, **kwargs) -> None:
        raise NotImplementedError("Escrow release is not enabled in this starter")

    async def refund_to_buyer(self, *args, **kwargs) -> None:
        raise NotImplementedError("Escrow refunds are not enabled in this starter")

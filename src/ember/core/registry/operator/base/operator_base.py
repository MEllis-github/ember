"""Core Operator Abstraction for Ember.

An Operator is an immutable, pure function with an associated Signature.
Operators are implemented as frozen dataclasses and automatically registered as PyTree nodes.
Subclasses must implement forward() to define their computation.
"""

from __future__ import annotations

import abc
import logging
from typing import Any, Dict, Generic, TypeVar, Union

from pydantic import BaseModel

from src.ember.core.utils.error_utils import wrap_forward_error, wrap_validation_error
from src.ember.core.registry.operator.base._module import EmberModule
from src.ember.core.registry.prompt_signature.signatures import Signature
from src.ember.core.registry.operator.exceptions import (
    OperatorSignatureNotDefinedError,
    SignatureValidationError,
    OperatorExecutionError,
)

logger = logging.getLogger(__name__)

# Type variables for the input and output Pydantic models.
T_in = TypeVar("T_in", bound=BaseModel)
T_out = TypeVar("T_out", bound=BaseModel)


class Operator(EmberModule, Generic[T_in, T_out], abc.ABC):
    """Abstract base class for an operator in Ember.

    Each operator must explicitly define its Signature (with required input and output models).
    This design encourages immutability and explicitness, aligning with functional programming
    principles and drawing inspiration from frameworks such as JAX Equinox.

    Attributes:
        signature (Signature): Contains the operator's input/output signature specification.
    """

    signature: Signature

    @abc.abstractmethod
    def forward(self, *, inputs: T_in) -> T_out:
        """Performs the operator's primary computation.

        Args:
            inputs (T_in): Validated input data.

        Returns:
            T_out: The computed output.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement forward()")

    def get_signature(self) -> Signature:
        """Retrieves the operator's signature.

        Returns:
            Signature: The operator's associated signature.

        Raises:
            OperatorSignatureNotDefinedError: If the signature has not been defined.
        """
        if not getattr(self, "signature", None):
            raise OperatorSignatureNotDefinedError(
                "Operator signature must be defined."
            )
        return self.signature

    def __call__(self, *, inputs: Union[T_in, Dict[str, Any]]) -> T_out:
        """Executes the operator by validating inputs, running the forward computation,
        and validating the output.

        Args:
            inputs (Union[T_in, Dict[str, Any]]): Either an already validated input model
            (T_in) or a raw dictionary that needs validation.

        Returns:
            The validated, computed output of type T_out.

        Raises:
            OperatorSignatureNotDefinedError: If this operator has no signature defined.
            SignatureValidationError: If input or output validation fails.
            OperatorExecutionError: If any error occurs in the forward computation.
        """
        signature: Signature = self.get_signature()

        # Validate inputs.
        validated_inputs: T_in = (
            signature.validate_inputs(inputs=inputs) if isinstance(inputs, dict) else inputs
        )

        # Run the forward computation.
        operator_output: T_out = self.forward(inputs=validated_inputs)

        # Validate output.
        validated_output: T_out = signature.validate_output(output=operator_output)

        return validated_output

from typing import Annotated

from pydantic import StringConstraints

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
# Solo dígitos ASCII, sin espacios: el RUC peruano tiene exactamente 11.
Ruc = Annotated[str, StringConstraints(pattern=r"^[0-9]{11}$")]

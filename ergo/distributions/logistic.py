"""
Logistic distribution
"""
from dataclasses import dataclass
from typing import Any, Optional

from jax import scipy
import jax.numpy as np
import scipy as oscipy

from ergo.scale import Scale

from .distribution import Distribution


@dataclass
class Logistic(Distribution):
    loc: float  # normalized
    s: float  # normalized
    scale: Scale
    metadata: Any = None

    def __init__(
        self,
        loc: float,
        s: float,
        scale: Optional[Scale] = None,
        metadata=None,
        normalized=False,
    ):
        # TODO (#303): Raise ValueError on scale < 0
        if normalized:
            self.loc = loc
            self.s = np.max([s, 0.0000001])
            self.metadata = metadata
            if scale is not None:
                self.scale = scale.copy()
            else:
                self.scale = Scale(0, 1)
            self.true_s = self.s * self.scale.width
            self.true_loc = self.scale.denormalize_point(loc)

        elif scale is None:
            raise ValueError("Either a Scale or normalized parameters are required")
        else:
            self.loc = scale.normalize_point(loc)
            self.s = np.max([s, 0.0000001]) / scale.width
            self.scale = scale.copy()
            self.metadata = metadata
            self.true_s = s
            self.true_loc = loc

        # TODO figure out a way to use the logistic function intregral in log-space to obviate this griding
        _xs = np.linspace(0, 1, 100)
        _true_xs = self.scale.denormalize_points(_xs)
        _densities = np.exp(
            scipy.stats.logistic.logpdf((_xs - self.loc) / self.s)
        ) - np.log(self.s)
        self.scale.norm_term = (
            _true_xs,
            _densities,  # these densities are norm-scaled normalized
            True,  # the densities are norm-scale normalized
        )

    def __repr__(self):
        return f"Logistic(scale={self.scale}, true_loc={self.true_loc}, true_s={self.true_s}, normed_loc={self.loc}, normed_s={self.s}, metadata={self.metadata})"

    # Distribution

    def pdf(self, x):
        y = (self.scale.normalize_point(x) - self.loc) / self.s
        p = np.exp(scipy.stats.logistic.logpdf(y) - np.log(self.s))
        return p / self.scale.norm_term

    def logpdf(self, x):
        y = (self.scale.normalize_point(x) - self.loc) / self.s
        logp = scipy.stats.logistic.logpdf(y) - np.log(self.s)
        return logp - np.log(self.scale.norm_term)

    def cdf(self, x):
        y = (self.scale.normalize_point(x) - self.loc) / self.s
        return scipy.stats.logistic.cdf(y)

    def ppf(self, q):
        return self.scale.denormalize_point(
            oscipy.stats.logistic(loc=self.loc, scale=self.s).ppf(q)
        )

    def sample(self):
        return self.scale.denormalize_point(
            oscipy.stats.logistic.rvs(loc=self.loc, scale=self.s)
        )

    # Scaled

    def normalize(self):
        """
        Return the normalized condition.

        :param scale: the true scale
        :return: the condition normalized to [0,1]
        """
        return self.__class__(
            self.loc, self.s, Scale(0, 1), self.metadata, normalized=True
        )

    def denormalize(self, scale: Scale):
        """
        Assume that the distribution has been normalized to be over [0,1].
        Return the distribution on the true scale

        :param scale: the true scale
        """
        return self.__class__(self.loc, self.s, scale, self.metadata, normalized=True)

    # Structured

    @classmethod
    def structure(self, params):
        class_params, numeric_params = params
        self_class, scale_classes = class_params
        self_numeric, scale_numeric = numeric_params
        scale = scale_classes[0].structure((scale_classes, scale_numeric))
        return self_class(
            loc=self_numeric[0], s=self_numeric[1], scale=scale, normalized=True
        )

    def destructure(self):
        scale_classes, scale_numeric = self.scale.destructure()
        class_params = (self.__class__, scale_classes)
        self_numeric = (self.loc, self.s)
        numeric_params = (self_numeric, scale_numeric)
        return (class_params, numeric_params)

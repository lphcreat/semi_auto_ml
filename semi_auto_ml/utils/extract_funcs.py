import pandas as pd
import numpy as np
import featuretools as ft

def format_importance(features,feature_importance):
    feature_importances = pd.DataFrame({'feature': features, 'importance': feature_importance})
    feature_importances = feature_importances.sort_values('importance', ascending = False).reset_index(drop = True)
    feature_importances['normalized_importance'] = feature_importances['importance'] / feature_importances['importance'].sum()
    feature_importances['cumulative_importance'] = np.cumsum(feature_importances['normalized_importance'])
    return feature_importances


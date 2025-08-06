function r=powertransform(gamma,model,data)

% POWERTRANSFORM    Computes negative correlation coefficient 
%
% Usage:
%
%        R = POWERTRANSFORM(GAMMA,MODEL,DATA)
%
% R        is the correlation between model and data, multiplied by -1
% GAMMA    is the exponent in the transformation
% MODEL    is the model predictions
% DATA     is the data to which predictions are compared

y = sign(model).*abs(model).^gamma;

inds = find(1-isnan(y));

if ((length(inds)>0)&(var(y(inds))>eps)&(gamma<10)&(gamma>0.1))
  cc = corrcoef(y(inds),data(inds));
  r = -cc(1,2);
else
  r = 1;
end


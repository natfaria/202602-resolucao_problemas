# Modelo de otimização: localização da formulação atual

Este caminho foi mantido para leitores de versões anteriores. A formulação autoritativa está em
[Modelo matemático de otimização de preços](modelo-matematico-otimizacao-precos.md).
As hipóteses antigas de suporte sempre rígido, custo previsto por seleção de janela e cenários
recebidos dos modelos `*_livro.json` não descrevem a execução atual.

A formulação atual distingue custo unitário constante, volume previsto, transição inicial e
mudanças internas. Extrapolação e sensibilidade de premissas são identificadas separadamente.

Para $q(p)=Ap^\beta$, $A>0$, $p>0$ e $\beta<0$, a demanda é convexa em preço:

$$q''(p)=A\beta(\beta-1)p^{\beta-2}>0.$$

Com $x=\ln p$, $q(e^x)=Ae^{\beta x}$ também é convexa, enquanto $\ln q$ é afim em $x$.
A receita líquida reescrita em volume é côncava quando $\beta<-1$; isso não torna o problema
completo convexo. Uma regra ativa no cenário foi imposta; uma restrição **vinculante na solução**
possui folga nula dentro da tolerância numérica. O domínio positivo de preço não está vinculante
nos planos admitidos pelo suporte observado.

O solver usa busca global com limitantes e gap. Múltiplos pontos iniciais não são condição de
validade do certificado. Consulte as [referências metodológicas](../referencias-bibliograficas.md).

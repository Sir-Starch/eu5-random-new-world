<!-- source: c1b2511ee47c687e -->

## Random New World

Um gerador de Novos Mundos para Europa Universalis V. Ele refaz as Américas do zero: continentes, costas, relevo, clima, rios, vegetação, recursos, províncias e povos nativos, e mantém o Velho Mundo como a Paradox o fez. **Cada mundo que ele cria é um mod de mapa completo por si só.** Ele roda sozinho: guarde quantos mundos quiser, exclua-os ou compartilhe o código de um mundo. O mundo funciona sem este gerador, e quem tiver a mesma versão do jogo cria o mesmo mundo a partir do código.

Você não ativa este item em nenhuma Condição de Jogo. Ele só traz o gerador.

## Por que há um programa neste item

O EU5 monta o mapa a partir de arquivos quando carrega os mods. Um mod é feito de dados: não consegue executar código. O script do jogo pode decidir quem é dono de quê no início, mas não pode criar terra, montanhas nem rios. O EU5 não oferece nenhuma forma oficial de adicionar código ao jogo.

Por isso, quem cria o mundo é um pequeno programa que vem com este item. Ele lê a sua instalação do EU5, cria um mundo e o salva como um mod comum. Não altera o jogo, não se conecta a ele e não roda dentro dele. O contrato de usuário da Paradox inclui programas entre os conteúdos que os jogadores podem criar e compartilhar de graça.

## Como usar

1. Na janela **Mods**, clique em **Abrir na pasta** em Random New World e dê um clique duplo em **Random New World Generator**.
2. Escolha um tipo de mundo: supercontinente, continentes, continentes pequenos, arquipélago ou ilhas espalhadas. Mantenha a semente aleatória, digite uma ou cole o código de um mundo. **O básico** responde em uma palavra às perguntas de sempre, como o Novo Mundo aleatório do EU4: quanta terra, quantos povos e Estados nativos, com que frequência surge um grande império nativo (nunca, raramente, às vezes, muitas vezes) e quanta riqueza em ouro e prata. Em **Personalizar** dá para mudar qualquer valor: terra, costas, escala do mapa e povos nativos, dos grandes impérios aos Estados isolados. Qualquer valor oferecido gera um mundo jogável.
3. Clique em **Criar**. Em dois ou três minutos o mundo aparece como um mod novo na sua lista, com um nome como "RNW: Small continents 7K3Q" (tipo de mundo e marca); você pode renomeá-lo no gerador. Enquanto o Novo Mundo estiver oculto, a imagem dele na lista de mods traz a mesma marca em vermelho, para os mundos não se confundirem.
4. No jogo, marque esse mundo (um mundo por vez) e comece um jogo novo. Se você já jogou uma campanha desde que abriu o EU5, reinicie o EU5 antes. O gerador diz exatamente o que fazer.

O gerador guarda cada mundo que você criou, com o código dele. Até você decidir mostrá-lo nas **Configurações**, o Novo Mundo continua terra incognita em todo lugar antes de você jogar: nas imagens do gerador, na lista de mods do jogo e no mapa da tela de novo jogo. Uma única configuração desliga tudo isso. O código de um mundo recria o mesmo mundo, byte por byte, em qualquer computador com a mesma versão do jogo.

O gerador fala todos os idiomas do jogo e abre no idioma em que a Steam executa o EU5.

## O que o programa faz e o que não faz

- Ele lê a sua instalação do EU5 e grava só em dois lugares: nos mundos que cria (`mod/rnw_world_…` na pasta do EU5 em Documentos) e na própria pasta de dados.
- Não usa a rede, não pede direitos de administrador, não mexe no registro e não altera nenhum arquivo do jogo.
- O código-fonte é público, sob a Mozilla Public License 2.0: https://github.com/Sir-Starch/eu5-random-new-world. Cada versão é compilada automaticamente a partir de um commit marcado, e a soma de verificação SHA-256 de cada arquivo é publicada lá.
- Confiar ou não em um programa é decisão sua. Você pode ler o código, comparar as somas de verificação ou compilá-lo por conta própria.

## Avisos do Windows

- Os arquivos que a Steam baixa não são marcados como vindos da internet, então o Windows SmartScreen não deve perguntar nada. [Confirm in 020.]
- Antivírus às vezes acusam programas novos que ainda não conhecem. A página de cada versão tem o link de uma verificação do VirusTotal.
- O Controle Inteligente de Aplicativos do Windows 11 bloqueia programas sem assinatura conhecida, e o Windows não permite exceção para um programa específico. [Until signed:] O gerador ainda não é assinado, então, com o Controle Inteligente de Aplicativos ativado, ele não abre. [Once signed:] O gerador e o módulo nativo dele são assinados por [signer].

## Linux e Steam Deck

O jogo roda pelo Proton. "Abrir na pasta" abre então o explorador de arquivos do Wine, e o mesmo gerador roda ali, dentro do prefixo do Proton do próprio jogo. Não é preciso instalar nada. [Steam Deck: confirm.]

## Limites

- **Só campanhas novas.** O mundo precisa ser criado antes de a campanha começar.
- **Crie antes de jogar ou reinicie.** O EU5 trava quando outro mundo começa depois de uma campanha na mesma sessão (o erro é do motor do jogo). Criar um mundo logo depois de abrir o EU5 não exige reiniciar; depois de uma campanha, reinicie o EU5 antes do mundo novo.
- **Atualizações do jogo.** Depois de uma atualização do EU5, o gerador pode se recusar a rodar até ser adaptado à nova versão. Aí ele oferece recriar o seu mundo. Jogos salvos antigos precisam do mundo em que foram jogados: crie-o de novo a partir do código.
- **Um mundo por vez.** Marque só um mundo criado em cada Condição de Jogo.
- **Multijogador.** Todos os jogadores usam o mesmo código de mundo e a mesma versão do jogo.
- **Memória.** Cerca de 7,5 GB de memória livre durante os dois minutos de criação. Os 32 GB recomendados para o EU5 dão e sobram.
- **Conquistas.** Como outros mods que alteram o jogo, ele muda a soma de verificação do jogo. [Confirm what EU5 allows.]

## Como remover

Exclua os mundos no gerador (**Excluir mundo**) ou apague você mesmo as pastas deles e depois cancele a inscrição. Os mundos que você mantiver continuam jogáveis sem o gerador.

## Licença e créditos

Código e arquivos do mod: Mozilla Public License 2.0. Os mundos são criados no seu computador a partir da sua cópia do EU5 e não são distribuídos pela Oficina. Europa Universalis V é uma marca registrada da Paradox Interactive; este mod não tem vínculo com a Paradox Interactive.
